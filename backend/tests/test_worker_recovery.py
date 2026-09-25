import pytest
from sqlalchemy import func, select

from app.db.models import Chunk, Document
from app.worker.queue import MSG_REPEATED_FAILURE, recover_interrupted

pytestmark = pytest.mark.integration


def _interrupted(session, name: str, attempts: int) -> Document:
    doc = Document(filename=name, file_hash=name.ljust(64, "0"), file_path="x", status="processing", attempts=attempts)
    session.add(doc)
    session.flush()
    session.add(Chunk(document_id=doc.id, page_number=1, chunk_index=0, content="parcial", token_count=1, embedding=[0.0] * 1024))
    session.commit()
    return doc


def test_interrupted_documents_are_requeued_or_failed_by_attempts(db_session):
    below = _interrupted(db_session, "abaixo", attempts=2)
    at_limit = _interrupted(db_session, "limite", attempts=3)
    ready = Document(filename="pronto", file_hash="p" * 64, file_path="x", status="ready", attempts=1)
    db_session.add(ready)
    db_session.commit()

    recover_interrupted(db_session, max_attempts=3)

    for doc in (below, at_limit, ready):
        db_session.refresh(doc)
    assert (below.status, below.error_message) == ("pending", None)
    assert (at_limit.status, at_limit.error_message) == ("failed", MSG_REPEATED_FAILURE)
    assert ready.status == "ready"
    assert db_session.scalar(select(func.count()).select_from(Chunk)) == 0
