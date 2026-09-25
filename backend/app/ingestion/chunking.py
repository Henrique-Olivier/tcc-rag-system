"""Extração por página e chunking (plano, seções 4 e 5.3). Trechos nunca cruzam páginas."""

import re
import unicodedata
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


# Linha só com o título da seção, numerado ou não, com dois-pontos opcional (seção 5.3).
_REFERENCES_HEADING = re.compile(
    r"^(\d+(\.\d+)*[.)]?\s*)?"
    r"(referencias( bibliograficas)?|references|bibliografia|bibliography|literatura citada|literature cited)"
    r"\s*:?$"
)


def _plain(line: str) -> str:
    """Sem acentos, minúsculas e espaços normalizados, para comparar com os títulos."""
    text = unicodedata.normalize("NFKD", line).encode("ascii", "ignore").decode()
    return " ".join(text.lower().split())


def strip_references(pages: list[tuple[int, str]]) -> tuple[list[tuple[int, str]], int | None]:
    """Remove a seção de referências, do título até o fim (plano, seção 5.3).

    Só vale título a partir da metade do documento, e vale o último. Devolve as páginas sem a seção
    e a página do título, ou as páginas intactas e None quando não há título.
    """
    found: tuple[int, int] | None = None  # (índice da página, posição do título no texto)
    for index in range(len(pages) // 2, len(pages)):
        offset = 0
        for line in pages[index][1].splitlines(keepends=True):
            if _REFERENCES_HEADING.match(_plain(line)):
                found = (index, offset)
            offset += len(line)
    if found is None:
        return pages, None
    index, offset = found
    page_number, text = pages[index]
    return [*pages[:index], (page_number, text[:offset])], page_number


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
