"""Verificações de arquivo da seção 5.3, nesta ordem: corrompido, senha, sem texto."""

from pathlib import Path

import pymupdf

MIN_CHARS_PER_PAGE = 50

MSG_CORRUPTED = "o arquivo está corrompido ou não é um PDF válido"
MSG_PASSWORD = "o PDF está protegido por senha"
MSG_NO_TEXT = "o arquivo parece ser escaneado (sem texto selecionável) e não pôde ser lido"


class PdfRejected(Exception):
    """PDF que não pode ser indexado; `message` vai para `documents.error_message` (CA03)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def open_checked_pdf(path: Path) -> pymupdf.Document:
    """Abre o PDF e devolve o documento, ou levanta PdfRejected com a mensagem para a usuária."""
    try:
        doc = pymupdf.open(path, filetype="pdf")
    except Exception as exc:
        raise PdfRejected(MSG_CORRUPTED) from exc
    if doc.page_count == 0:
        doc.close()
        raise PdfRejected(MSG_CORRUPTED)
    if doc.needs_pass:
        doc.close()
        raise PdfRejected(MSG_PASSWORD)
    chars = sum(len(page.get_text().strip()) for page in doc)
    if chars / doc.page_count < MIN_CHARS_PER_PAGE:
        doc.close()
        raise PdfRejected(MSG_NO_TEXT)
    return doc
