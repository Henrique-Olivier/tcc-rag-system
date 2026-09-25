import hashlib
import threading
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.ingestion.upload import Outcome, UploadedFile, register_uploads

pytestmark = pytest.mark.integration

MAX_MB = 1


def _pdf(tag: str) -> UploadedFile:
    return UploadedFile(f"{tag}.pdf", b"%PDF-1.4\n" + tag.encode())


def _existing(session: Session, file: UploadedFile, status: str, deleted: bool, with_chunk: bool = False) -> Document:
    doc = Document(filename=file.filename, file_hash=hashlib.sha256(file.data).hexdigest(), file_path="x",
                   status=status, attempts=3, error_message="erro" if status == "failed" else None,
                   deleted_at=datetime.now(UTC) if deleted else None)
    session.add(doc)
    session.flush()
    if with_chunk:
        session.add(Chunk(document_id=doc.id, page_number=1, chunk_index=0, content="c", token_count=1, embedding=[0.0] * 1024))
    session.commit()
    return doc


def _upload(session, tmp_path, *files):
    return register_uploads(session, list(files), tmp_path, MAX_MB)


def test_new_file_is_saved_by_hash_and_queued(db_session, tmp_path):
    file = _pdf("novo")
    [result] = _upload(db_session, tmp_path, file)

    doc = db_session.get(Document, result.document_id)
    assert result.outcome == Outcome.NEW
    assert (doc.status, doc.filename) == ("pending", "novo.pdf")
    assert (tmp_path / f"{doc.file_hash}.pdf").read_bytes() == file.data


@pytest.mark.parametrize("status", ["ready", "pending", "processing"])
def test_active_file_is_duplicate_and_unchanged(db_session, tmp_path, status):
    file = _pdf("ativo")
    doc = _existing(db_session, file, status, deleted=False)

    [result] = _upload(db_session, tmp_path, file)

    db_session.refresh(doc)
    assert result.outcome == Outcome.DUPLICATE
    assert (doc.status, doc.attempts) == (status, 3)


@pytest.mark.parametrize("deleted", [False, True])
def test_failed_file_is_reprocessed(db_session, tmp_path, deleted):
    file = _pdf("falhou")
    doc = _existing(db_session, file, "failed", deleted=deleted, with_chunk=True)

    [result] = _upload(db_session, tmp_path, file)

    db_session.refresh(doc)
    assert result.outcome == Outcome.REPROCESSED
    assert (doc.status, doc.error_message, doc.attempts, doc.deleted_at) == ("pending", None, 0, None)
    assert db_session.scalar(select(func.count()).select_from(Chunk)) == 0


@pytest.mark.parametrize("status", ["ready", "pending", "processing"])
def test_deleted_file_is_reactivated_without_reprocessing(db_session, tmp_path, status):
    file = _pdf("removido")
    doc = _existing(db_session, file, status, deleted=True, with_chunk=True)

    [result] = _upload(db_session, tmp_path, file)

    db_session.refresh(doc)
    assert result.outcome == Outcome.REACTIVATED
    assert (doc.status, doc.deleted_at, doc.attempts) == (status, None, 3)
    assert db_session.scalar(select(func.count()).select_from(Chunk)) == 1


def test_non_pdf_and_oversized_files_are_rejected(db_session, tmp_path):
    results = _upload(db_session, tmp_path, UploadedFile("nota.docx", b"PK\x03\x04"),
                      UploadedFile("grande.pdf", b"%PDF-" + b"0" * (MAX_MB * 1024 * 1024)))

    assert [r.outcome for r in results] == [Outcome.REJECTED, Outcome.REJECTED]
    assert db_session.scalar(select(func.count()).select_from(Document)) == 0
    assert list(tmp_path.iterdir()) == []


def test_same_file_twice_in_request(db_session, tmp_path):
    results = _upload(db_session, tmp_path, _pdf("a"), _pdf("a"))

    assert [r.outcome for r in results] == [Outcome.NEW, Outcome.DUPLICATE]
    assert db_session.scalar(select(func.count()).select_from(Document)) == 1


def test_concurrent_uploads_of_same_file(engine, db_session, tmp_path):
    file, barrier, outcomes = _pdf("corrida"), threading.Barrier(2), []

    def upload():
        with Session(engine) as session:
            barrier.wait()
            outcomes.extend(r.outcome for r in register_uploads(session, [file], tmp_path, MAX_MB))

    threads = [threading.Thread(target=upload) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(outcomes) == [Outcome.DUPLICATE, Outcome.NEW]
    assert db_session.scalar(select(func.count()).select_from(Document)) == 1


def test_uploaded_name_never_becomes_a_path(db_session, tmp_path):
    data_dir = tmp_path / "pdfs"
    [result] = register_uploads(db_session, [UploadedFile("../fora.pdf", b"%PDF-1.4 x")], data_dir, MAX_MB)

    doc = db_session.get(Document, result.document_id)
    assert doc.filename == "../fora.pdf"
    assert [p.name for p in data_dir.iterdir()] == [f"{doc.file_hash}.pdf"]
    assert not (tmp_path / "fora.pdf").exists()
