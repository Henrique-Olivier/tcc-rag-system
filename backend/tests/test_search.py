from datetime import UTC, datetime

import pytest

from app.db.models import Chunk, Document
from app.retrieval.search import search
from tests.fakes import unit_vector

pytestmark = pytest.mark.integration

QUERY = unit_vector(1.0)


def _doc(session, name: str, status: str = "ready", deleted: bool = False) -> Document:
    doc = Document(filename=f"{name}.pdf", file_hash=name.ljust(64, "0"), file_path="x", status=status,
                   deleted_at=datetime.now(UTC) if deleted else None)
    session.add(doc)
    session.flush()
    return doc


def _chunk(session, doc: Document, content: str, vector: list[float], page: int = 1) -> None:
    session.add(Chunk(document_id=doc.id, page_number=page, chunk_index=0, content=content, token_count=1, embedding=vector))


@pytest.fixture
def corpus(db_session):
    ready = _doc(db_session, "pronto")
    _chunk(db_session, ready, "idêntico", unit_vector(1.0), page=3)
    _chunk(db_session, ready, "próximo", unit_vector(0.8, 0.6))
    _chunk(db_session, ready, "distante", unit_vector(0.0, 1.0))
    for name, status, deleted in [("removido", "ready", True), ("pendente", "pending", False), ("falhou", "failed", False)]:
        _chunk(db_session, _doc(db_session, name, status, deleted), f"de {name}", unit_vector(1.0))
    db_session.commit()


def test_results_are_ordered_by_similarity(db_session, corpus):
    results = search(db_session, QUERY, top_k=8, min_similarity=-1.0)

    assert [r.content for r in results] == ["idêntico", "próximo", "distante"]
    assert [round(r.similarity, 3) for r in results] == [1.0, 0.8, 0.0]
    assert (results[0].filename, results[0].page_number) == ("pronto.pdf", 3)


def test_only_ready_active_documents_are_searched(db_session, corpus):
    contents = {r.content for r in search(db_session, QUERY, top_k=8, min_similarity=-1.0)}

    assert contents.isdisjoint({"de removido", "de pendente", "de falhou"})


def test_threshold_drops_weak_chunks_and_top_k_limits(db_session, corpus):
    assert [r.content for r in search(db_session, QUERY, top_k=8, min_similarity=0.5)] == ["idêntico", "próximo"]
    assert [r.content for r in search(db_session, QUERY, top_k=1, min_similarity=0.0)] == ["idêntico"]


def test_nothing_above_threshold_returns_empty(db_session, corpus):
    assert search(db_session, unit_vector(0.0, 0.0, 1.0), top_k=8, min_similarity=0.3) == []
