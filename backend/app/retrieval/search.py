"""Busca vetorial exata (plano, seções 6 e 6.3). Sem índice: com 10 a 15 mil vetores a varredura leva milissegundos."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    filename: str
    page_number: int
    content: str
    similarity: float  # 1 - distância de cosseno


def search(session: Session, query_vector: list[float], top_k: int, min_similarity: float) -> list[RetrievedChunk]:
    """Os `top_k` trechos mais próximos de documentos prontos e ativos, sem os abaixo do limiar (CA05, CA08)."""
    distance = Chunk.embedding.cosine_distance(query_vector).label("distance")
    rows = session.execute(
        select(Chunk, Document.filename, distance)
        .join(Document, Document.id == Chunk.document_id)
        .where(Document.status == "ready", Document.deleted_at.is_(None))
        .order_by(distance)
        .limit(top_k)
    )
    results = [
        RetrievedChunk(chunk.id, chunk.document_id, filename, chunk.page_number, chunk.content, 1 - dist)
        for chunk, filename, dist in rows
    ]
    return [r for r in results if r.similarity >= min_similarity]
