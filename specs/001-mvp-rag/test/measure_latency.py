"""T27: tempo entre o envio da pergunta e o fim da resposta, com o sistema ocioso e com o worker indexando.

Uso (a partir de backend/): uv run python ../specs/001-mvp-rag/test/measure_latency.py
Usa Q01 a Q05 do questions.yaml (test/README.md). Para o cenário com indexação, envia um PDF
sintético de 80 páginas (~6 min de indexação), faz as perguntas enquanto ele está em `processing` e o remove no fim.
Critério: até ~15 s nos dois cenários (RNF da spec). Espera entre perguntas pelo limite do Groq.
"""

import random
import time
from pathlib import Path

import httpx
import pymupdf
import yaml

HERE = Path(__file__).parent
API = "http://127.0.0.1:8000"
PAUSE_SECONDS = 65
LIMIT_SECONDS = 15

questions = [q["question"] for q in yaml.safe_load((HERE / "questions.yaml").read_text(encoding="utf-8"))["questions"][:5]]


def load_pdf() -> bytes:
    """80 páginas densas, diferentes a cada execução: ocupam o worker durante as 5 perguntas."""
    words = "renal feline serum creatinine phosphorus clinical study cohort treatment dose response plasma".split()
    rng = random.Random()
    pdf = pymupdf.open()
    for _ in range(80):
        text = " ".join(rng.choice(words) for _ in range(450))
        pdf.new_page().insert_textbox(pymupdf.Rect(40, 40, 560, 800), text, fontsize=9)
    return pdf.tobytes()


def timed_answer(client: httpx.Client, question: str) -> tuple[float, str]:
    conversation_id = client.post("/conversations").json()["id"]
    started = time.perf_counter()
    last_event = ""
    with client.stream("POST", f"/conversations/{conversation_id}/messages", json={"content": question}) as response:
        for line in response.iter_lines():
            if line.startswith("event: "):
                last_event = line.removeprefix("event: ")
    elapsed = time.perf_counter() - started
    client.delete(f"/conversations/{conversation_id}")
    return elapsed, last_event


def scenario(client: httpx.Client, name: str, document_id: int | None = None) -> list[float]:
    times = []
    for index, question in enumerate(questions):
        if index:
            time.sleep(PAUSE_SECONDS)
        state = client.get(f"/documents/{document_id}").json()["status"] if document_id else "-"
        elapsed, last_event = timed_answer(client, question)
        times.append(elapsed)
        print(f"  {name} Q0{index + 1}: {elapsed:5.1f} s ({last_event}; carga: {state})")
    return times


with httpx.Client(base_url=API, timeout=180) as client:
    idle = scenario(client, "ocioso")
    time.sleep(PAUSE_SECONDS)
    [upload] = client.post("/documents", files=[("files", ("carga_latencia.pdf", load_pdf(), "application/pdf"))]).json()
    while client.get(f"/documents/{upload['document_id']}").json()["status"] != "processing":
        time.sleep(1)
    busy = scenario(client, "indexando", upload["document_id"])
    client.delete(f"/documents/{upload['document_id']}")

for name, times in (("ocioso", idle), ("indexando", busy)):
    status = "ok" if max(times) <= LIMIT_SECONDS else "ACIMA DO LIMITE"
    print(f"{name}: média {sum(times) / len(times):.1f} s, máximo {max(times):.1f} s -> {status}")
