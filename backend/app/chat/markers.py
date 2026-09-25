"""Parser de marcadores de citação (plano, seção 6.4)."""

import re

_ITEM = r"\d+(?:\s*[-–]\s*\d+)?"
MARKER_RE = re.compile(rf"\[\s*({_ITEM}(?:\s*,\s*{_ITEM})*)\s*\]")
_RANGE_SEP = re.compile(r"\s*[-–]\s*")


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
