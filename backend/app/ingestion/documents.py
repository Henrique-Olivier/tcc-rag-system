"""Consultas de documentos ativos, posição na fila e soft delete (plano, seções 4 e 8)."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import Document


@dataclass(frozen=True)
class DocumentView:
    document: Document
    queue_position: int | None  # só para `pending`; nulo nos demais status


def _with_queue_position() -> Select:
    # Mesma ordem em que o worker consome a fila (seção 5.2).
    queue = (
        select(Document.id, func.row_number().over(order_by=(Document.created_at, Document.id)).label("position"))
        .where(Document.status == "pending", Document.deleted_at.is_(None))
        .subquery()
    )
    return select(Document, queue.c.position).outerjoin(queue, queue.c.id == Document.id).where(Document.deleted_at.is_(None))


def list_active(session: Session) -> list[DocumentView]:
    rows = session.execute(_with_queue_position().order_by(Document.created_at.desc(), Document.id.desc()))
    return [DocumentView(doc, position) for doc, position in rows]


def get_active(session: Session, document_id: int) -> DocumentView | None:
    row = session.execute(_with_queue_position().where(Document.id == document_id)).first()
    return DocumentView(*row) if row else None


def soft_delete(session: Session, document_id: int) -> bool:
    """Chunks e citações ficam; a busca e o histórico filtram por `deleted_at` (CA05, CA16)."""
    document = session.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        return False
    document.deleted_at = datetime.now(UTC)
    session.commit()
    return True
