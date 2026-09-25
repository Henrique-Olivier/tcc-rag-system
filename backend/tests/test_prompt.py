from app.chat.history import HistoryTurn
from app.chat.prompt import build_answer_messages
from app.retrieval.search import RetrievedChunk


def _source(chunk_id: int, filename: str, page: int, content: str) -> RetrievedChunk:
    return RetrievedChunk(chunk_id, 1, filename, page, content, 0.9)


SOURCES = [_source(7, "gatos.pdf", 3, "Meloxicam em felinos."), _source(2, "caes.pdf", 10, "Carprofeno em cães.")]


def test_sources_are_numbered_in_order_with_file_and_page():
    system, user = build_answer_messages("Qual o AINE para gatos?", SOURCES, history=[])

    assert system["role"] == "system" and "[n]" in system["content"]
    assert "[1] (gatos.pdf, p. 3)\nMeloxicam em felinos." in user["content"]
    assert "[2] (caes.pdf, p. 10)\nCarprofeno em cães." in user["content"]
    assert user["content"].index("[1]") < user["content"].index("[2]")
    assert user["content"].rstrip().endswith("Pergunta: Qual o AINE para gatos?")


def test_history_only_inside_delimited_section():
    history = [HistoryTurn("E a dose?", "0,1 mg/kg (gatos.pdf, p. 3)"), HistoryTurn("E em idosos?", None)]
    _, user = build_answer_messages("E em cães?", SOURCES, history)
    content = user["content"]

    section = content[content.index("<historico>") : content.index("</historico>")]
    assert "Resposta: 0,1 mg/kg (gatos.pdf, p. 3)" in section
    assert "Pergunta: E em idosos?" in section
    outside = content.replace(section, "")
    assert "0,1 mg/kg" not in outside and "E em idosos?" not in outside


def test_no_history_means_no_section():
    _, user = build_answer_messages("Pergunta", SOURCES, history=[])

    assert "<historico>" not in user["content"]


def test_instructions_carry_context_rules_and_a_parseable_example():
    import re

    from app.chat.markers import parse_markers
    from app.chat.prompt import ANSWER_INSTRUCTIONS

    assert "aspas" in ANSWER_INSTRUCTIONS and "idioma original" in ANSWER_INSTRUCTIONS
    assert "espécie" in ANSWER_INSTRUCTIONS and "cães" in ANSWER_INSTRUCTIONS
    assert "efeito colateral, conclusão ou recomendação" in ANSWER_INSTRUCTIONS
    example = re.search(r"Exemplo do formato de citação:\n(.+)\n", ANSWER_INSTRUCTIONS).group(1)
    assert parse_markers(example, num_sources=3) == [1, 2, 3]
