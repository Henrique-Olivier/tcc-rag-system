"""T11: mede o tempo de indexação dos PDFs de uma pasta, pelo sistema rodando no Docker.

Uso (a partir de backend/): uv run python ../specs/001-mvp-rag/test/measure_indexing.py "C:/caminho/dos/pdfs"
Envia todos numa requisição, consulta GET /documents a cada 0,5 s e registra quando cada um
entra em `processing` e fica `ready`. Não mede documentos que voltarem como duplicados.
"""

import sys
import time
from pathlib import Path

import httpx
import pymupdf

API = "http://127.0.0.1:8000"
TARGET_PAGES = 100 * 50  # cenário da spec: 100 documentos de 50 páginas

folder = Path(sys.argv[1])
paths = sorted(folder.glob("*.pdf"))
pages = {p.name: pymupdf.open(p).page_count for p in paths}

with httpx.Client(base_url=API, timeout=300) as client:
    started = time.perf_counter()
    results = client.post("/documents", files=[("files", (p.name, p.read_bytes(), "application/pdf")) for p in paths]).json()
    ids = {r["document_id"]: r["filename"] for r in results if r["outcome"] == "new"}
    skipped = [f"{r['filename']} ({r['outcome']})" for r in results if r["outcome"] != "new"]
    if skipped:
        print("fora da medição:", ", ".join(skipped))

    began: dict[int, float] = {}
    finished: dict[int, float] = {}
    status: dict[int, str] = {}
    while len(finished) < len(ids):
        now = time.perf_counter() - started
        for doc in client.get("/documents").json():
            if doc["id"] not in ids:
                continue
            status[doc["id"]] = doc["status"]
            if doc["status"] in ("processing", "ready", "failed"):
                began.setdefault(doc["id"], now)
            if doc["status"] in ("ready", "failed"):
                finished.setdefault(doc["id"], now)
        time.sleep(0.5)
    total = time.perf_counter() - started

print(f"\n{'arquivo':48} {'pág':>4} {'status':>8} {'processamento':>14} {'s/pág':>6}")
processing_total = 0.0
for doc_id, name in ids.items():
    duration = finished[doc_id] - began[doc_id]
    processing_total += duration
    print(f"{name:48} {pages[name]:>4} {status[doc_id]:>8} {duration:>13.1f}s {duration / pages[name]:>6.2f}")

measured_pages = sum(pages[name] for doc_id, name in ids.items() if status[doc_id] == "ready")
per_page = processing_total / measured_pages
print(f"\ntotal: {len(ids)} documentos, {measured_pages} páginas indexadas em {total:.1f}s de relógio")
print(f"média: {per_page:.2f} s/página (só processamento, sem espera na fila)")
print(f"extrapolação para {TARGET_PAGES} páginas: {per_page * TARGET_PAGES / 3600:.1f} h")
