"""Dublês compartilhados pelos testes."""

import re


class WordTokenizer:
    """Uma palavra = um token, com offsets como o tokenizador do Hugging Face."""

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=True):
        return {"offset_mapping": [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]}


def unit_vector(*head: float) -> list[float]:
    """Vetor de 1024 dimensões com os primeiros valores dados e o resto zero."""
    return list(head) + [0.0] * (1024 - len(head))


class FakeEmbedder:
    tokenizer = WordTokenizer()

    def __init__(self, vector: list[float] | None = None, fail_on: str | None = None) -> None:
        self.vector = vector or unit_vector(1.0)
        self.fail_on = fail_on

    def encode(self, texts):
        if self.fail_on and any(self.fail_on in t for t in texts):
            raise RuntimeError("falha simulada")
        return [self.vector for _ in texts]
