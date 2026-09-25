"""T26, parte 1: acerto da busca e calibração de MIN_SIMILARITY e TOP_K (plano, seções 6.3 e 12).

Uso (a partir de backend/): PYTHONPATH=. uv run python ../specs/001-mvp-rag/test/eval_retrieval.py
Lê questions.yaml, gera o embedding de cada pergunta com o mesmo bge-m3 e busca no banco da
aplicação (via 127.0.0.1) sem limiar. As sequências de acompanhamento ficam de fora: no sistema
a busca delas usa a pergunta reescrita, avaliada na parte 2 (respostas).
"""

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.embeddings.model import Embedder
from app.retrieval.search import search

HERE = Path(__file__).parent
MAX_K = 12
K_VALUES = (4, 6, 8, 10, 12)


class _Env(BaseSettings):
    model_config = SettingsConfigDict(env_file=HERE.parents[2] / ".env", extra="ignore")
    postgres_user: str
    postgres_password: str
    postgres_db: str
    embedding_model: str = "BAAI/bge-m3"


def hit_rank(results, expected, min_docs: int) -> tuple[int | None, float | None]:
    """Posição (1-based) em que a pergunta passa a contar como acerto e a similaridade do trecho que decidiu."""
    wanted = {(e["doc"], page) for e in expected for page in e["pages"]}
    docs_found: set[str] = set()
    for rank, r in enumerate(results, start=1):
        if (r.doc_id, r.page_number) in wanted:
            docs_found.add(r.doc_id)
            if len(docs_found) >= min_docs:
                return rank, r.similarity
    return None, None


env = _Env()
spec = yaml.safe_load((HERE / "questions.yaml").read_text(encoding="utf-8"))
doc_ids = {filename: doc_id for doc_id, filename in spec["documents"].items()}
engine = create_engine(URL.create("postgresql+psycopg", env.postgres_user, env.postgres_password, "127.0.0.1", 5432, env.postgres_db))
embedder = Embedder(env.embedding_model, num_threads=4)

rows = []
with Session(engine) as session:
    for q in spec["questions"]:
        [vector] = embedder.encode([q["question"]])
        results = search(session, vector, top_k=MAX_K, min_similarity=-1.0)
        for r in results:
            object.__setattr__(r, "doc_id", doc_ids.get(r.filename, "outro"))
        rank, sim = hit_rank(results, q["expected"], q.get("min_docs", 1)) if q["expected"] else (None, None)
        rows.append((q, results, rank, sim))

print(f"{'id':4} {'tipo':14} {'acerto@8':>8} {'posição':>7} {'sim acerto':>10} {'sim máx':>8}  top-4 (doc:pág sim)")
for q, results, rank, sim in rows:
    top = " ".join(f"{r.doc_id}:{r.page_number} {r.similarity:.2f}" for r in results[:4])
    answerable = bool(q["expected"])
    hit8 = ("sim" if rank and rank <= 8 else "NÃO") if answerable else "-"
    sim_text = "-" if sim is None else f"{sim:.3f}"
    print(f"{q['id']:4} {q['type']:14} {hit8:>8} {rank or '-':>7} {sim_text:>10} "
          f"{results[0].similarity:>8.3f}  {top}")

answerable = [(q, rank, sim) for q, _, rank, sim in rows if q["expected"]]
no_answer = [(q, results[0].similarity) for q, results, _, _ in rows if not q["expected"]]
print("\nAcerto por TOP_K (perguntas com resposta):")
for k in K_VALUES:
    hits = sum(1 for _, rank, _ in answerable if rank and rank <= k)
    print(f"  TOP_K={k:>2}: {hits}/{len(answerable)}")

hit_sims = [sim for _, rank, sim in answerable if rank and rank <= 8]
print(f"\nMenor similaridade de um trecho que decidiu um acerto (TOP_K=8): {min(hit_sims):.3f}")
print("Maior similaridade nas perguntas sem resposta:", ", ".join(f"{q['id']}={s:.3f}" for q, s in no_answer))
print("Limiar máximo que não barra nenhum acerto: qualquer valor até", f"{min(hit_sims):.3f}")
