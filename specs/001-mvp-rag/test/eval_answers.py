"""Respostas reais para a avaliação dos CAs 06 a 09 e 11 (plano v11, seção 12).

Uso (a partir de backend/): uv run python ../specs/001-mvp-rag/test/eval_answers.py --model openai/gpt-oss-120b
O `--model` só identifica o relatório: o modelo usado é o `LLM_ANSWER_MODEL` da api (troque no .env e
recrie a api para comparar modelos).
Faz cada pergunta do questions.yaml numa conversa nova (as sequências na mesma conversa) contra o
sistema no Docker, com o Groq de verdade, e grava test/answers-AAAA-MM-DD.md para revisão. Espera
entre perguntas por causa do limite de tokens por minuto do Groq (seção 6.7). Apaga as conversas
de teste no fim, para não poluir a lista dela.
"""

import argparse
import json
import re
import time
from datetime import date
from pathlib import Path

import httpx
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, create_engine, text

HERE = Path(__file__).parent
API = "http://127.0.0.1:8000"
PAUSE_SECONDS = 65
# Sem repetição: repetir na mesma conversa cria histórico e muda a busca (reescrita). Num 429 o
# script para; rode as perguntas restantes depois com --only.
RATE_LIMIT_RETRIES = 0


class _Env(BaseSettings):
    model_config = SettingsConfigDict(env_file=HERE.parents[2] / ".env", extra="ignore")
    postgres_user: str
    postgres_password: str
    postgres_db: str


env = _Env()
engine = create_engine(URL.create("postgresql+psycopg", env.postgres_user, env.postgres_password, "127.0.0.1", 5432, env.postgres_db))
spec = yaml.safe_load((HERE / "questions.yaml").read_text(encoding="utf-8"))
doc_ids = {filename: doc_id for doc_id, filename in spec["documents"].items()}


def ask(client: httpx.Client, conversation_id: int, question: str) -> dict:
    """Uma pergunta por SSE; repete se o Groq devolver limite por minuto."""
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        result = {"sources": [], "answer": "", "markers": [], "uncited": False, "error": None}
        started = time.perf_counter()
        with client.stream("POST", f"/conversations/{conversation_id}/messages", json={"content": question}) as response:
            if response.status_code != 200:
                return {**result, "error": f"HTTP {response.status_code}: {response.read().decode()}"}
            event = None
            for line in response.iter_lines():
                if line.startswith("event: "):
                    event = line.removeprefix("event: ")
                elif line.startswith("data: "):
                    data = json.loads(line.removeprefix("data: "))
                    if event == "sources":
                        result["sources"] = data["sources"]
                    elif event == "token":
                        result["answer"] += data["text"]
                    elif event == "done":
                        result["markers"] = data["markers"]
                        result["uncited"] = data.get("uncited", False)
                    elif event == "error":
                        result["error"] = data["message"]
        result["seconds"] = time.perf_counter() - started
        if not (result["error"] and "limite" in result["error"]) or attempt == RATE_LIMIT_RETRIES:
            return result
        print(f"   limite do Groq; nova tentativa em {PAUSE_SECONDS}s")
        time.sleep(PAUSE_SECONDS)
    return result


def rewritten(conversation_id: int, question: str) -> str | None:
    with engine.connect() as conn:
        return conn.scalar(
            text("SELECT rewritten_query FROM messages WHERE conversation_id = :c AND role = 'user' AND content = :q ORDER BY id DESC LIMIT 1"),
            {"c": conversation_id, "q": question},
        )


def metrics(result: dict, expected: list) -> dict:
    """Métricas automáticas da seção 12; a precisão da citação continua manual."""
    if not expected:
        return {"recall": None, "doc_cited": None, "uncited": result["uncited"]}
    wanted_pages = {(e["doc"], page) for e in expected for page in e["pages"]}
    wanted_docs = {e["doc"] for e in expected}
    sent = [(doc_ids.get(s["filename"]), s["page_number"]) for s in result["sources"]]
    cited_docs = {doc_ids.get(s["filename"]) for s in result["sources"] if s["marker"] in result["markers"]}
    return {"recall": any(p in wanted_pages for p in sent), "doc_cited": bool(cited_docs & wanted_docs),
            "uncited": result["uncited"]}


def yes_no(value) -> str:
    return "-" if value is None else ("sim" if value else "NÃO")


def section(item_id: str, turn: dict, conversation_id: int, result: dict, m: dict) -> str:
    lines = [f"### {item_id} — {turn['question']}", ""]
    if query := rewritten(conversation_id, turn["question"]):
        lines += [f"**Pergunta reescrita:** {query}", ""]
    lines += [f"**Tempo:** {result.get('seconds', 0):.1f} s · **Recuperação:** {yes_no(m['recall'])} · "
              f"**Citação no documento esperado:** {yes_no(m['doc_cited'])} · **Sem citação (uncited):** {yes_no(m['uncited'])}", ""]
    if result["error"]:
        lines += [f"**Erro:** {result['error']}", ""]
    lines += ["**Resposta:**", "", result["answer"] or "_(vazia)_", "", "**Trechos enviados:**", ""]
    for s in result["sources"]:
        mark = " ✓ citado" if s["marker"] in result["markers"] else ""
        lines.append(f"- [{s['marker']}] {doc_ids.get(s['filename'], s['filename'])} p. {s['page_number']} "
                     f"(similaridade {s.get('similarity', 0):.3f}){mark}")
    lines += ["", "**Esperado:** " + (", ".join(f"{e['doc']} p. {e['pages']}" for e in turn.get("expected", [])) or "nenhum documento (sem resposta)")]
    if turn.get("key_facts"):
        lines += ["", "**Deve conter:**", *[f"- {fact}" for fact in turn["key_facts"]]]
    if turn.get("notes"):
        lines += ["", f"**Observação:** {turn['notes']}"]
    lines += ["", "**Avaliação manual:** ☐ fundamentada (CA06) ☐ citações certas (CA07) ☐ sem inventar (CA08) ☐ português (CA09)", ""]
    return "\n".join(lines)


parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True, help="modelo configurado na api, para identificar o relatório")
parser.add_argument("--only", help="ids separados por vírgula, ex.: F01,F02 (padrão: todos)")
args = parser.parse_args()
model = args.model

items = [(q["id"], [q]) for q in spec["questions"]] + [(f["id"], f["turns"]) for f in spec["follow_ups"]]
if args.only:
    items = [item for item in items if item[0] in args.only.split(",")]
report: list[str] = []
summary: list[tuple[str, dict, float]] = []
created: list[int] = []
with httpx.Client(base_url=API, timeout=180) as client:
    for index, (item_id, turns) in enumerate(items):
        conversation_id = client.post("/conversations").json()["id"]
        created.append(conversation_id)
        for turn_number, turn in enumerate(turns, start=1):
            if index or turn_number > 1:
                time.sleep(PAUSE_SECONDS)
            label = item_id if len(turns) == 1 else f"{item_id}.{turn_number}"
            print(f"{label}: {turn['question']}")
            result = ask(client, conversation_id, turn["question"])
            m = metrics(result, turn.get("expected", []))
            summary.append((label, m, result.get("seconds", 0)))
            report.append(section(label, turn, conversation_id, result, m))
            if result["error"] and "limite" in result["error"]:
                report.append("_Interrompido: limite do Groq atingido. Rodar de novo depois para as perguntas restantes._")
                break
        else:
            continue
        break
    for conversation_id in created:
        client.delete(f"/conversations/{conversation_id}")

answerable = [m for _, m, _ in summary if m["recall"] is not None]
header = [f"# Respostas do conjunto simulado — {model} — {date.today():%d/%m/%Y}", "",
          "Gerado por `eval_answers.py` contra o sistema no Docker (Groq real). Marque a avaliação manual de cada item.", "",
          "## Resumo", "",
          f"- Recuperação (página esperada entre os trechos enviados): {sum(m['recall'] for m in answerable)}/{len(answerable)}",
          f"- Citação no documento esperado: {sum(m['doc_cited'] for m in answerable)}/{len(answerable)}",
          f"- Respostas sem citação (`uncited`): {sum(m['uncited'] for _, m, _ in summary)}/{len(summary)}",
          f"- Tempo médio: {sum(s for _, _, s in summary) / max(len(summary), 1):.1f} s", "",
          "| Item | Recuperação | Citação no doc. esperado | Sem citação |", "|---|---|---|---|",
          *[f"| {label} | {yes_no(m['recall'])} | {yes_no(m['doc_cited'])} | {yes_no(m['uncited'])} |" for label, m, _ in summary],
          ""]
slug = re.sub(r"[^a-z0-9.-]+", "-", model.lower()).strip("-")
suffix = f"-{args.only.replace(',', '-')}" if args.only else ""
out = HERE / f"answers-{date.today():%Y-%m-%d}-{slug}{suffix}.md"
out.write_text("\n".join(header + report), encoding="utf-8")
print(f"relatório: {out}")
