from datetime import UTC, datetime

import pymupdf
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.models import Chunk, Citation, Conversation, Document, Message
from app.worker.reindex import reindex_all
from tests.fakes import FakeEmbedder, unit_vector

pytestmark = pytest.mark.integration

TEXT = "Meloxicam foi usado como analgésico em gatos após cirurgia. " * 20


def _ready_document(session, tmp_path, name: str, deleted: bool = False) -> Document:
    """Documento pronto com um trecho antigo, como estava antes da reindexação."""
    path = tmp_path / f"{name}.pdf"
    pdf = pymupdf.open()
    for text in (TEXT, TEXT + "\nReferences\nSILVA, A. 2020."):
        pdf.new_page().insert_textbox(pymupdf.Rect(40, 40, 560, 800), text)
    pdf.save(path)
    doc = Document(filename=f"{name}.pdf", file_hash=name.ljust(64, "0"), file_path=str(path), status="ready",
                   deleted_at=datetime.now(UTC) if deleted else None)
    session.add(doc)
    session.flush()
    session.add(Chunk(document_id=doc.id, page_number=2, chunk_index=0, content="trecho antigo com SILVA",
                      token_count=4, embedding=unit_vector(1.0)))
    session.commit()
    return doc


def _contents(session, document_id) -> list[str]:
    session.expire_all()
    return session.scalars(select(Chunk.content).where(Chunk.document_id == document_id)).all()


def test_chunks_are_replaced_and_documents_stay_ready_or_removed(engine, db_session, tmp_path):
    active = _ready_document(db_session, tmp_path, "ativo")
    removed = _ready_document(db_session, tmp_path, "removido", deleted=True)

    assert reindex_all(sessionmaker(engine), FakeEmbedder(), 50, 10) == (2, 0)

    for doc in (active, removed):
        db_session.refresh(doc)
        contents = _contents(db_session, doc.id)
        assert doc.status == "ready" and doc.references_start_page == 2
        assert contents and "trecho antigo com SILVA" not in contents
        assert not any("SILVA" in c for c in contents)
    assert removed.deleted_at is not None


def test_saved_citation_survives_reindex(engine, db_session, tmp_path):
    doc = _ready_document(db_session, tmp_path, "citado")
    [old_chunk] = db_session.scalars(select(Chunk).where(Chunk.document_id == doc.id)).all()
    conversation = Conversation()
    db_session.add(conversation)
    db_session.flush()
    answer = Message(conversation_id=conversation.id, role="assistant", content="Resposta [1].")
    db_session.add(answer)
    db_session.flush()
    db_session.add(Citation(message_id=answer.id, chunk_id=old_chunk.id, document_id=doc.id, marker=1,
                            filename="citado.pdf", page_number=2, excerpt="trecho antigo com SILVA"))
    db_session.commit()

    reindex_all(sessionmaker(engine), FakeEmbedder(), 50, 10)

    db_session.expire_all()
    citation = db_session.scalars(select(Citation)).one()
    assert (citation.chunk_id, citation.excerpt, citation.page_number) == (None, "trecho antigo com SILVA", 2)


def test_failure_keeps_old_chunks_and_next_document_is_processed(engine, db_session, tmp_path):
    broken = _ready_document(db_session, tmp_path, "quebrado")
    good = _ready_document(db_session, tmp_path, "bom")
    class FailsFirst(FakeEmbedder):
        calls = 0

        def encode(self, texts):
            self.calls += 1
            if self.calls == 1:  # só o primeiro documento falha
                raise RuntimeError("falha simulada")
            return super().encode(texts)

    assert reindex_all(sessionmaker(engine), FailsFirst(), 50, 10) == (1, 1)
    assert _contents(db_session, broken.id) == ["trecho antigo com SILVA"]
    assert "trecho antigo com SILVA" not in _contents(db_session, good.id)
    db_session.refresh(broken)
    assert broken.status == "ready"
