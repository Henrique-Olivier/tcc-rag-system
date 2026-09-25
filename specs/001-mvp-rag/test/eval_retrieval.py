"""Avaliação da busca (plano v11, seções 6.3 e 12): posição da página esperada entre os 30 trechos mais similares.

Uso (a partir de backend/): PYTHONPATH=. uv run python ../specs/001-mvp-rag/test/eval_retrieval.py [--top-k 8]
Lê questions.yaml, gera o embedding de cada pergunta com o mesmo bge-m3 e busca no banco da
aplicação (via 127.0.0.1) sem limiar. Grava test/retrieval-AAAA-MM-DD.md. As sequências de
acompanhamento ficam de fora: no sistema a busca delas usa a pergunta reescrita (ver eval_answers.py).
"""

import argparse
from datetime import date
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.embeddings.model import Embedder
from app.retrieval.search import search

HERE = Path(__file__).parent
DEPTH = 30


class _Env(BaseSettings):
    model_config = SettingsConfigDict(env_file=HERE.parents[2] / ".env", extra="ignore")
    postgres_user: str
    postgres_password: str
    postgres_db: str
    embedding_model: str = "BAAI/bge-m3"
    top_k: int = 8


def expected_rank(results, expected, min_docs: int) -> int | None:
    """Posição (1-based) em que a pergunta passa a contar como acerto; None se não acontece nos 30."""
    wanted = {(e["doc"], page) for e in expected for page in e["pages"]}
    docs_found: set[str] = set()
    for rank, (doc_id, page, _) in enumerate(results, start=1):
        if (doc_id, page) in wanted:
            docs_found.add(doc_id)
            if len(docs_found) >= min_docs:
                return rank
    return None


def main() -> None:
    env = _Env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=env.top_k)
    top_k = parser.parse_args().top_k

    spec = yaml.safe_load((HERE / "questions.yaml").read_text(encoding="utf-8"))
    doc_ids = {filename: doc_id for doc_id, filename in spec["documents"].items()}
    engine = create_engine(URL.create("postgresql+psycopg", env.postgres_user, env.postgres_password, "127.0.0.1", 5432, env.postgres_db))
    embedder = Embedder(env.embedding_model, num_threads=4)

    rows = []
    with Session(engine) as session:
        for q in spec["questions"]:
            [vector] = embedder.encode([q["question"]])
            found = search(session, vector, top_k=DEPTH, min_similarity=-1.0)
            results = [(doc_ids.get(r.filename, "outro"), r.page_number, r.similarity) for r in found]
            rank = expected_rank(results, q["expected"], q.get("min_docs", 1)) if q["expected"] else None
            rows.append((q, results, rank))

    lines = [f"# Avaliação da busca — {date.today():%d/%m/%Y}", "",
             f"Gerado por `eval_retrieval.py`. TOP_K avaliado: {top_k}. Posição = onde a página esperada aparece entre os {DEPTH} trechos mais similares.", "",
             "| Pergunta | Tipo | Posição da página esperada | Recuperação no TOP_K | Similaridade dos trechos enviados |",
             "|---|---|---|---|---|"]
    for q, results, rank in rows:
        sent = ", ".join(f"{d}:{p} {s:.2f}" for d, p, s in results[:top_k])
        if not q["expected"]:
            position, recall = "sem resposta esperada", "-"
        else:
            position = str(rank) if rank else f"fora dos {DEPTH}"
            recall = "sim" if rank and rank <= top_k else "NÃO"
        lines.append(f"| {q['id']} | {q['type']} | {position} | {recall} | {sent} |")

    answerable = [rank for q, _, rank in rows if q["expected"]]
    lines += ["", "## Resumo", "", "| TOP_K | Recuperação |", "|---|---|"]
    for k in sorted({4, 6, 8, 10, 12, top_k}):
        lines.append(f"| {k} | {sum(1 for r in answerable if r and r <= k)}/{len(answerable)} |")
    misses = [(q["id"], rank) for q, _, rank in rows if q["expected"] and not (rank and rank <= top_k)]
    lines += ["", "Falhas com o TOP_K avaliado: " + (", ".join(f"{i} (posição {r or f'fora dos {DEPTH}'})" for i, r in misses) or "nenhuma")]
    no_answer = [f"{q['id']}={results[0][2]:.3f}" for q, results, _ in rows if not q["expected"]]
    lines.append("Maior similaridade nas perguntas sem resposta: " + ", ".join(no_answer))

    out = HERE / f"retrieval-{date.today():%Y-%m-%d}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-12:]))
    print(f"relatório: {out}")


if __name__ == "__main__":
    main()
