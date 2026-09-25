from datetime import UTC, datetime

import pymupdf
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Chunk, Document
from app.ingestion.pdf_checks import MSG_NO_TEXT
from app.worker.queue import MSG_UNEXPECTED, claim_next, process_document, run_once
from tests.fakes import FakeEmbedder

pytestmark = pytest.mark.integration

TEXT = "Meloxicam foi usado como analgésico em gatos após cirurgia. " * 20


def _document(session, tmp_path, name: str, pages: list[str]) -> Document:
    path = tmp_path / f"{name}.pdf"
    pdf = pymupdf.open()
    for text in pages:
        pdf.new_page().insert_textbox(pymupdf.Rect(40, 40, 560, 800), text)
    pdf.save(path)
    doc = Document(filename=f"{name}.pdf", file_hash=name.ljust(64, "0"), file_path=str(path))
    session.add(doc)
    session.commit()
    return doc


def _chunk_count(session, document_id) -> int:
    return session.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id))


def test_valid_document_becomes_ready_with_chunks(engine, db_session, tmp_path):
    doc = _document(db_session, tmp_path, "valido", [TEXT, TEXT])

    assert run_once(sessionmaker(engine), FakeEmbedder(), chunk_size=50, chunk_overlap=10)

    db_session.refresh(doc)
    assert (doc.status, doc.num_pages, doc.attempts) == ("ready", 2, 1)
    assert _chunk_count(db_session, doc.id) > 2
    assert not run_once(sessionmaker(engine), FakeEmbedder(), 50, 10)


def test_pdf_without_text_fails_with_message(engine, db_session, tmp_path):
    doc = _document(db_session, tmp_path, "escaneado", ["", ""])

    run_once(sessionmaker(engine), FakeEmbedder(), 50, 10)

    db_session.refresh(doc)
    assert (doc.status, doc.error_message) == ("failed", MSG_NO_TEXT)


def test_unexpected_error_fails_document_and_next_is_processed(engine, db_session, tmp_path):
    bad = _document(db_session, tmp_path, "ruim", ["Documento problemático. " * 20])
    good = _document(db_session, tmp_path, "bom", [TEXT])
    embedder = FakeEmbedder(fail_on="problemático")

    run_once(sessionmaker(engine), embedder, 50, 10)
    run_once(sessionmaker(engine), embedder, 50, 10)

    db_session.refresh(bad)
    db_session.refresh(good)
    assert (bad.status, bad.error_message, _chunk_count(db_session, bad.id)) == ("failed", MSG_UNEXPECTED, 0)
    assert good.status == "ready"


def test_two_consumers_never_claim_the_same_document(engine, db_session, tmp_path):
    first = _document(db_session, tmp_path, "primeiro", [TEXT])
    second = _document(db_session, tmp_path, "segundo", [TEXT])

    with Session(engine) as holder, Session(engine) as other:
        # Outro consumidor está no meio da reivindicação do primeiro (linha travada).
        locked = holder.scalar(select(Document).where(Document.id == first.id).with_for_update())
        assert locked is not None
        assert claim_next(other) == second.id
        assert claim_next(other) is None


def test_deleted_pending_document_is_not_claimed(db_session, tmp_path):
    doc = _document(db_session, tmp_path, "removido", [TEXT])
    doc.deleted_at = datetime.now(UTC)
    db_session.commit()

    assert claim_next(db_session) is None


def test_document_deleted_during_processing_finishes_and_stays_deleted(engine, db_session, tmp_path):
    doc = _document(db_session, tmp_path, "durante", [TEXT])

    with Session(engine) as worker_session:
        claimed = claim_next(worker_session)
        worker_session.get(Document, claimed)  # worker já carregou o documento
        with Session(engine) as api_session:  # usuária remove enquanto o worker processa
            api_session.get(Document, claimed).deleted_at = datetime.now(UTC)
            api_session.commit()
        process_document(worker_session, claimed, FakeEmbedder(), 50, 10)

    db_session.refresh(doc)
    assert doc.status == "ready"
    assert doc.deleted_at is not None
    assert _chunk_count(db_session, doc.id) > 0
