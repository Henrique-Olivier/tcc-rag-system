"""Parser de marcadores de citação (plano, seção 6.4)."""

import re

_ITEM = r"\d+(?:\s*[-–]\s*\d+)?"
MARKER_RE = re.compile(rf"\[\s*({_ITEM}(?:\s*,\s*{_ITEM})*)\s*\]")
_RANGE_SEP = re.compile(r"\s*[-–]\s*")
# O gpt-oss cita como 【1】; um caractere por colchete, então nunca fica partido entre pedaços do streaming.
_WIDE_BRACKETS = str.maketrans({"【": "[", "】": "]", "［": "[", "］": "]"})


def normalize_brackets(text: str) -> str:
    """Colchetes largos viram [ ] para o parser, o front e o banco verem só [n] (plano v7)."""
    return text.translate(_WIDE_BRACKETS)


# O gpt-oss às vezes anexa a linha de origem: [2†L20-L23]. Pode vir partido entre pedaços do streaming,
# então é removido no texto completo (plano v10).
_DAGGER_SUFFIX = re.compile(r"†[^\[\]]*(?=\])")


def strip_citation_suffixes(text: str) -> str:
    """[2†L20-L23] -> [2]."""
    return _DAGGER_SUFFIX.sub("", text)


def expand_marker(group: str, upper: int) -> list[int]:
    """"1, 3-5" -> [1, 3, 4, 5], sem passar de `upper`. Intervalos invertidos são ignorados."""
    numbers: list[int] = []
    for item in group.split(","):
        bounds = [int(n) for n in _RANGE_SEP.split(item.strip())]
        numbers.extend(range(bounds[0], min(bounds[-1], upper) + 1))
    return numbers


def parse_markers(text: str, num_sources: int) -> list[int]:
    """Marcadores válidos (1..num_sources), na ordem da primeira aparição e sem repetição."""
    found: list[int] = []
    for match in MARKER_RE.finditer(text):
        for number in expand_marker(match.group(1), num_sources):
            if 1 <= number <= num_sources and number not in found:
                found.append(number)
    return found
