"""Verificações de ingestão do questions.yaml contra o sistema no Docker.

Uso (a partir de backend/): uv run python ../specs/001-mvp-rag/test/ingestion_checks.py "C:/caminho/dos/pdfs"
- D5: PDF só com imagem (gerado aqui) termina `failed` com a mensagem de escaneado (CA03);
  reenviado, é reprocessado e falha de novo.
- D1: reenviar um arquivo já indexado volta como duplicado (CA04).
"""

import sys
import time
from pathlib import Path

import httpx
import pymupdf

API = "http://127.0.0.1:8000"


def scanned_pdf() -> bytes:
    """Página com texto rasterizado: parece um documento, mas não tem texto extraível."""
    source = pymupdf.open()
    source.new_page().insert_textbox(pymupdf.Rect(50, 50, 550, 800), "Anotações da aula de nefrologia felina. " * 30)
    image = source[0].get_pixmap(dpi=100).tobytes("png")
    pdf = pymupdf.open()
    for _ in range(2):
        pdf.new_page().insert_image(pymupdf.Rect(0, 0, 595, 842), stream=image)
    return pdf.tobytes()


def upload(client: httpx.Client, name: str, data: bytes) -> dict:
    [result] = client.post("/documents", files=[("files", (name, data, "application/pdf"))]).json()
    return result


def wait_final(client: httpx.Client, doc_id: int) -> dict:
    for _ in range(120):
        doc = client.get(f"/documents/{doc_id}").json()
        if doc["status"] in ("ready", "failed"):
            return doc
        time.sleep(1)
    raise TimeoutError(doc_id)


with httpx.Client(base_url=API, timeout=120) as client:
    data = scanned_pdf()
    first = upload(client, "anotacoes_aula_escaneado.pdf", data)
    doc = wait_final(client, first["document_id"])
    print(f"D5 envio: {first['outcome']} -> {doc['status']}: {doc['error_message']}")
    assert doc["status"] == "failed" and "escaneado" in doc["error_message"]

    again = upload(client, "anotacoes_aula_escaneado.pdf", data)
    doc = wait_final(client, again["document_id"])
    print(f"D5 reenvio: {again['outcome']} -> {doc['status']}")
    assert again["outcome"] == "reprocessed" and doc["status"] == "failed"

    d1 = Path(sys.argv[1]) / "freitas2025_vetworld_pressao_proteinuria.pdf"
    result = upload(client, d1.name, d1.read_bytes())
    print(f"D1 reenvio: {result['outcome']}")
    assert result["outcome"] == "duplicate"

    client.delete(f"/documents/{first['document_id']}")  # não deixa o D5 na lista dela
    print("verificações de ingestão ok")
