"""Extração por página e chunking (plano, seções 4 e 5.3). Trechos nunca cruzam páginas."""

from dataclasses import dataclass

import pymupdf
from transformers import PreTrainedTokenizerBase


@dataclass(frozen=True)
class TextChunk:
    page_number: int  # a partir de 1
    chunk_index: int  # sequencial no documento
    content: str
    token_count: int


def extract_pages(doc: pymupdf.Document) -> list[tuple[int, str]]:
    """(page_number, texto); o PyMuPDF numera a partir de 0, o banco a partir de 1."""
    return [(index + 1, page.get_text()) for index, page in enumerate(doc)]


def chunk_pages(
    pages: list[tuple[int, str]], tokenizer: PreTrainedTokenizerBase, size: int, overlap: int
) -> list[TextChunk]:
    if not 0 <= overlap < size:
        raise ValueError("CHUNK_OVERLAP precisa ser menor que CHUNK_SIZE")
    chunks: list[TextChunk] = []
    for page_number, text in pages:
        offsets = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        start = 0
        while start < len(offsets):
            window = offsets[start : start + size]
            # Fatia do texto original, sem reconstruir a partir dos tokens.
            content = text[window[0][0] : window[-1][1]].strip()
            if content:
                chunks.append(TextChunk(page_number, len(chunks), content, len(window)))
            if start + size >= len(offsets):
                break
            start += size - overlap
    return chunks
