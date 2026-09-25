"""Regras de upload da seção 5.1. Sem FastAPI: a rota só converte a requisição e chama `register_uploads`."""

import hashlib
import os
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document

PDF_SIGNATURE = b"%PDF-"


class Outcome(StrEnum):
    NEW = "new"
    DUPLICATE = "duplicate"
    REPROCESSED = "reprocessed"
    REACTIVATED = "reactivated"
    REJECTED = "rejected"


@dataclass(frozen=True)
class UploadedFile:
    filename: str  # só para exibição; nunca entra em caminhos (seção 4)
    data: bytes


@dataclass(frozen=True)
class UploadResult:
    filename: str
    outcome: Outcome
    document_id: int | None = None
    message: str | None = None


def register_uploads(session: Session, files: list[UploadedFile], data_dir: Path, max_upload_mb: int) -> list[UploadResult]:
    """Aplica as regras a cada arquivo, na ordem recebida. Cada arquivo tem sua própria transação."""
    results: list[UploadResult] = []
    seen: set[str] = set()
    for file in files:
        if rejection := _rejection(file, max_upload_mb):
            results.append(UploadResult(file.filename, Outcome.REJECTED, message=rejection))
            continue
        file_hash = hashlib.sha256(file.data).hexdigest()
        if file_hash in seen:
            results.append(UploadResult(file.filename, Outcome.DUPLICATE, message="arquivo repetido neste envio"))
            continue
        seen.add(file_hash)
        results.append(_register_one(session, file, file_hash, data_dir))
    return results


def _rejection(file: UploadedFile, max_upload_mb: int) -> str | None:
    if len(file.data) > max_upload_mb * 1024 * 1024:
        return f"o arquivo passa do limite de {max_upload_mb} MB"
    if not file.data.startswith(PDF_SIGNATURE):
        return "o arquivo não é um PDF"
    return None


def _register_one(session: Session, file: UploadedFile, file_hash: str, data_dir: Path) -> UploadResult:
    path = data_dir / f"{file_hash}.pdf"
    existing = session.scalar(select(Document).where(Document.file_hash == file_hash).with_for_update())

    if existing is None:
        _write_atomically(path, file.data)
        document = Document(filename=file.filename, file_hash=file_hash, file_path=str(path), status="pending")
        session.add(document)
        try:
            session.commit()
        except IntegrityError:  # outro upload do mesmo arquivo venceu a corrida (CA04)
            session.rollback()
            return UploadResult(file.filename, Outcome.DUPLICATE)
        return UploadResult(file.filename, Outcome.NEW, document.id)

    if existing.status == "failed":  # falha pode ser transitória: tenta de novo (CA03)
        session.execute(delete(Chunk).where(Chunk.document_id == existing.id))
        existing.status, existing.error_message, existing.attempts, existing.deleted_at = "pending", None, 0, None
        if not path.exists():
            _write_atomically(path, file.data)
        outcome = Outcome.REPROCESSED
    elif existing.deleted_at is not None:  # ready: disponível na hora; pending/processing: segue na fila (CA17)
        existing.deleted_at = None
        outcome = Outcome.REACTIVATED
    else:
        outcome = Outcome.DUPLICATE  # ativo e ready, pending ou processing (CA04)
    session.commit()
    return UploadResult(file.filename, outcome, existing.id)


def _write_atomically(path: Path, data: bytes) -> None:
    """O worker nunca vê um PDF pela metade."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "wb") as out:
        out.write(data)
    os.replace(tmp, path)
