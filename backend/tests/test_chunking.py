import pymupdf
import pytest
from transformers import AutoTokenizer

from app.core.config import Settings
from app.ingestion.chunking import chunk_pages, extract_pages, strip_references

SIZE, OVERLAP = 50, 10
LONG = " ".join(f"felino{i} recebeu dose{i} de meloxicam." for i in range(60))


@pytest.fixture(scope="module")
def tokenizer():
    return AutoTokenizer.from_pretrained(Settings.model_fields["embedding_model"].default)


def test_pages_are_numbered_from_one():
    doc = pymupdf.open()
    for text in ["primeira", "segunda"]:
        doc.new_page().insert_text((72, 72), text)

    assert [(n, t.strip()) for n, t in extract_pages(doc)] == [(1, "primeira"), (2, "segunda")]


def test_chunks_never_cross_pages(tokenizer):
    chunks = chunk_pages([(1, LONG), (2, "página curta"), (3, LONG)], tokenizer, SIZE, OVERLAP)

    assert {c.page_number for c in chunks} == {1, 2, 3}
    for chunk in chunks:
        page_text = {1: LONG, 2: "página curta", 3: LONG}[chunk.page_number]
        assert chunk.content in page_text
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_size_and_overlap_follow_configuration(tokenizer):
    chunks = chunk_pages([(1, LONG)], tokenizer, SIZE, OVERLAP)
    total = len(tokenizer(LONG, add_special_tokens=False)["input_ids"])

    assert len(chunks) > 1
    assert all(c.token_count <= SIZE for c in chunks)
    assert all(c.token_count == SIZE for c in chunks[:-1])
    # Cada janela anda SIZE - OVERLAP tokens, e a última termina no fim da página.
    assert (len(chunks) - 1) * (SIZE - OVERLAP) + chunks[-1].token_count == total
    for previous, current in zip(chunks, chunks[1:]):
        assert current.content[:15] in previous.content


def test_short_page_becomes_single_chunk_and_blank_page_none(tokenizer):
    chunks = chunk_pages([(1, "Página curta."), (2, "   \n ")], tokenizer, SIZE, OVERLAP)

    assert [(c.page_number, c.content) for c in chunks] == [(1, "Página curta.")]


def test_overlap_must_be_smaller_than_size(tokenizer):
    with pytest.raises(ValueError):
        chunk_pages([(1, LONG)], tokenizer, size=10, overlap=10)


def _pages(*texts: str) -> list[tuple[int, str]]:
    return [(n, text) for n, text in enumerate(texts, start=1)]


@pytest.mark.parametrize("heading", ["Referências", "REFERENCES", "7. References:", "Literatura citada", "Referências Bibliográficas"])
def test_references_heading_variants_are_cut(heading):
    pages = _pages("Introdução.", "Métodos.", "Resultados.", f"Conclusão final.\n{heading}\nSILVA, A. Artigo. 2020.\n", "SOUZA, B. 2021.")

    kept, start = strip_references(pages)

    assert start == 4
    assert kept == _pages("Introdução.", "Métodos.", "Resultados.", "Conclusão final.\n")


def test_word_inside_a_sentence_is_not_a_heading():
    pages = _pages("a", "b", "c", "As referências citadas abaixo foram revisadas.\n")

    assert strip_references(pages) == (pages, None)


def test_heading_in_first_half_is_ignored_and_last_one_wins():
    pages = _pages("Sumário\nReferências\n", "b", "Referências\nparcial\n", "texto\nReferences\nFIM\n")

    kept, start = strip_references(pages)

    assert start == 4
    assert kept[0] == (1, "Sumário\nReferências\n")
    assert kept[-1] == (4, "texto\n")


def test_document_without_heading_is_kept_whole():
    pages = _pages("Anotações da aula.", "Mais anotações.")

    assert strip_references(pages) == (pages, None)
