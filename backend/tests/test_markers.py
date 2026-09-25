import pytest

from app.chat.markers import parse_markers


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A dose foi segura [1].", [1]),
        ("Dois estudos [1, 3] concordam.", [1, 3]),
        ("Vários trabalhos [2-4].", [2, 3, 4]),
        ("Vários trabalhos [2–4].", [2, 3, 4]),
        ("Misto [1, 3-4] e repetido [1].", [1, 3, 4]),
        ("Ordem de aparição [5] antes de [2].", [5, 2]),
        ("Sem citações.", []),
        ("Não é marcador: [a] nem [].", []),
    ],
)
def test_parse_markers(text, expected):
    assert parse_markers(text, num_sources=6) == expected


def test_numbers_outside_sent_sources_are_ignored():
    assert parse_markers("Fora [9], zero [0], parcial [5-8], enorme [1-999999999].", num_sources=6) == [5, 6, 1, 2, 3, 4]


def test_dagger_line_suffixes_are_stripped():
    from app.chat.markers import strip_citation_suffixes

    text = strip_citation_suffixes("Entre 2,7 e 5,0 mg/dL [2†L20-L23][3†L14-L18].")

    assert text == "Entre 2,7 e 5,0 mg/dL [2][3]."
    assert parse_markers(text, num_sources=3) == [2, 3]


def test_wide_brackets_from_gpt_oss_are_normalized():
    from app.chat.markers import normalize_brackets

    text = normalize_brackets("Dose segura【1】 e ［2, 3］.")

    assert text == "Dose segura[1] e [2, 3]."
    assert parse_markers(text, num_sources=3) == [1, 2, 3]
