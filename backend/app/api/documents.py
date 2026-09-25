from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.deps import get_session
from app.ingestion.documents import DocumentView, get_active, list_active, soft_delete
from app.ingestion.upload import Outcome, UploadedFile, register_uploads

router = APIRouter(prefix="/documents", tags=["documentos"])

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


class UploadResultOut(BaseModel):
    filename: str
    outcome: Outcome
    document_id: int | None
    message: str | None


class DocumentOut(BaseModel):
    id: int
    filename: str
    status: str
    error_message: str | None
    num_pages: int | None
    created_at: datetime
    queue_position: int | None

    @classmethod
    def of(cls, view: DocumentView) -> "DocumentOut":
        doc = view.document
        return cls(id=doc.id, filename=doc.filename, status=doc.status, error_message=doc.error_message,
                   num_pages=doc.num_pages, created_at=doc.created_at, queue_position=view.queue_position)


@router.post("", response_model=list[UploadResultOut])
async def upload_documents(files: list[UploadFile], session: SessionDep, settings: SettingsDep):
    limit = settings.max_upload_mb * 1024 * 1024
    # Lê no máximo limite + 1 byte: arquivo grande é recusado sem ir inteiro para a memória.
    uploaded = [UploadedFile(f.filename or "sem nome.pdf", await f.read(limit + 1)) for f in files]
    return await run_in_threadpool(register_uploads, session, uploaded, settings.data_dir, settings.max_upload_mb)


@router.get("", response_model=list[DocumentOut])
def list_documents(session: SessionDep):
    return [DocumentOut.of(view) for view in list_active(session)]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, session: SessionDep):
    return DocumentOut.of(_active_or_404(session, document_id))


@router.get("/{document_id}/file")
def get_document_file(document_id: int, session: SessionDep):
    doc = _active_or_404(session, document_id).document
    return FileResponse(doc.file_path, media_type="application/pdf", filename=doc.filename, content_disposition_type="inline")


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, session: SessionDep):
    if not soft_delete(session, document_id):
        raise HTTPException(404, "documento não encontrado")


def _active_or_404(session: Session, document_id: int) -> DocumentView:
    view = get_active(session, document_id)
    if view is None:
        raise HTTPException(404, "documento não encontrado")
    return view
