"""Reindexação dos documentos prontos (plano, seção 5.6).

Uso, dentro do container do worker: `nice -n 10 python -m app.worker.reindex`.
"""

import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Chunk, Document
from app.worker.queue import EmbeddingModel, build_chunks

log = logging.getLogger("worker")


def reindex_document(session: Session, document_id: int, embedder: EmbeddingModel, chunk_size: int, chunk_overlap: int) -> bool:
    """Troca os trechos numa só transação: o documento nunca fica sem trechos nem sai da busca.

    Numa falha, a transação é desfeita e os trechos antigos continuam valendo.
    """
    document = session.get(Document, document_id)
    try:
        chunks = build_chunks(document, embedder, chunk_size, chunk_overlap)
        # Citações antigas ficam com chunk_id nulo e mantêm as cópias (seção 4).
        session.execute(delete(Chunk).where(Chunk.document_id == document_id))
        session.add_all(chunks)
        session.commit()
    except Exception:
        session.rollback()
        log.exception("falha ao reindexar o documento %s; trechos antigos mantidos", document_id)
        return False
    log.info("documento %s reindexado: %s trechos", document_id, len(chunks))
    return True


def reindex_all(sessions: sessionmaker[Session], embedder: EmbeddingModel, chunk_size: int, chunk_overlap: int) -> tuple[int, int]:
    """Todos os documentos `ready`, inclusive os removidos (para voltarem já reindexados se reativados)."""
    with sessions() as session:
        ids = session.scalars(select(Document.id).where(Document.status == "ready").order_by(Document.id)).all()
    ok = 0
    for document_id in ids:
        with sessions() as session:
            ok += reindex_document(session, document_id, embedder, chunk_size, chunk_overlap)
    return ok, len(ids) - ok


def main() -> None:
    from app.core.config import get_settings
    from app.db.session import get_sessionmaker
    from app.embeddings.model import Embedder

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    embedder = Embedder(settings.embedding_model, settings.worker_torch_threads)
    ok, failed = reindex_all(get_sessionmaker(), embedder, settings.chunk_size, settings.chunk_overlap)
    log.info("reindexação concluída: %s documentos reindexados, %s com falha", ok, failed)


if __name__ == "__main__":
    main()
