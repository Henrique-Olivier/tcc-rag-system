"""Fila de ingestão no banco e processamento de um documento (plano, seções 5.2 e 5.3)."""

import logging
from pathlib import Path
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Chunk, Document
from app.ingestion.chunking import chunk_pages, extract_pages, strip_references
from app.ingestion.pdf_checks import PdfRejected, open_checked_pdf

log = logging.getLogger("worker")

MSG_UNEXPECTED = "erro inesperado ao processar o arquivo"
MSG_REPEATED_FAILURE = "o processamento deste arquivo falhou repetidamente"


class EmbeddingModel(Protocol):
    @property
    def tokenizer(self): ...

    def encode(self, texts: list[str]) -> list[list[float]]: ...


def claim_next(session: Session) -> int | None:
    """Reivindica o documento pendente mais antigo; `processing` e `attempts + 1` na mesma transação."""
    document = session.scalar(
        select(Document)
        .where(Document.status == "pending", Document.deleted_at.is_(None))
        .order_by(Document.created_at, Document.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if document is None:
        session.rollback()
        return None
    document.status = "processing"
    document.attempts += 1
    session.commit()
    return document.id


def build_chunks(document: Document, embedder: EmbeddingModel, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """Verificações, extração sem referências, trechos e embeddings; preenche `num_pages` e `references_start_page`.

    Usado pelo worker e pela reindexação (seção 5.6). Não grava nada: quem chama decide a transação.
    """
    with open_checked_pdf(Path(document.file_path)) as pdf:
        pages, references_page = strip_references(extract_pages(pdf))
        document.num_pages = pdf.page_count
    document.references_start_page = references_page
    if references_page is None:
        log.info("documento %s sem seção de referências identificada; indexado inteiro", document.id)
    chunks = chunk_pages(pages, embedder.tokenizer, chunk_size, chunk_overlap)
    vectors = embedder.encode([chunk.content for chunk in chunks])
    return [
        Chunk(document_id=document.id, page_number=c.page_number, chunk_index=c.chunk_index,
              content=c.content, token_count=c.token_count, embedding=v)
        for c, v in zip(chunks, vectors, strict=True)
    ]


def process_document(session: Session, document_id: int, embedder: EmbeddingModel, chunk_size: int, chunk_overlap: int) -> None:
    """Nenhuma exceção escapa: falhas viram `failed` e o worker segue para o próximo (seção 5.3)."""
    document = session.get(Document, document_id)
    try:
        chunks = build_chunks(document, embedder, chunk_size, chunk_overlap)
        session.add_all(chunks)
        # Só as colunas alteradas vão no UPDATE: um soft delete feito durante o processamento é preservado.
        document.status, document.error_message = "ready", None
        session.commit()
        log.info("documento %s pronto: %s páginas, %s trechos", document_id, document.num_pages, len(chunks))
    except PdfRejected as exc:
        _mark_failed(session, document_id, exc.message)
    except Exception:
        log.exception("erro inesperado no documento %s", document_id)
        _mark_failed(session, document_id, MSG_UNEXPECTED)


def _mark_failed(session: Session, document_id: int, message: str) -> None:
    session.rollback()  # descarta trechos gravados pela metade
    document = session.get(Document, document_id)
    document.status, document.error_message = "failed", message
    session.commit()


def run_once(sessions: sessionmaker[Session], embedder: EmbeddingModel, chunk_size: int, chunk_overlap: int) -> bool:
    """Processa um documento da fila. Devolve False quando a fila está vazia."""
    with sessions() as session:
        document_id = claim_next(session)
        if document_id is None:
            return False
        process_document(session, document_id, embedder, chunk_size, chunk_overlap)
        return True


def recover_interrupted(session: Session, max_attempts: int) -> None:
    """Na inicialização: `processing` só existe se o processo anterior morreu no meio (seção 5.2).

    O limite de tentativas impede que um arquivo que derruba o processo trave a fila.
    """
    for document in session.scalars(select(Document).where(Document.status == "processing")):
        session.execute(delete(Chunk).where(Chunk.document_id == document.id))
        if document.attempts < max_attempts:
            document.status = "pending"
        else:
            document.status, document.error_message = "failed", MSG_REPEATED_FAILURE
        log.warning("documento %s interrompido: %s (tentativa %s)", document.id, document.status, document.attempts)
    session.commit()
