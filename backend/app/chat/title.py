"""Título da conversa (plano, seção 6.8)."""

import logging

from app.llm.provider import LLMProvider

log = logging.getLogger("api")

MAX_WORDS = 6
FALLBACK_CHARS = 60

TITLE_INSTRUCTIONS = (
    "Crie um título curto, de até 6 palavras, em português, para uma conversa de pesquisa que começa com a pergunta "
    "abaixo. Responda somente com o título, sem aspas e sem ponto final."
)


def fallback_title(question: str) -> str:
    """Primeira pergunta truncada, sem cortar palavra no meio."""
    text = " ".join(question.split())
    if len(text) <= FALLBACK_CHARS:
        return text
    return text[:FALLBACK_CHARS].rsplit(" ", 1)[0] + "…"


async def generate_title(llm: LLMProvider, model: str, question: str) -> str:
    try:
        raw = await llm.complete(model, [{"role": "system", "content": TITLE_INSTRUCTIONS}, {"role": "user", "content": question}])
    except Exception:
        log.warning("falha ao gerar o título; usando a pergunta", exc_info=True)
        return fallback_title(question)
    words = raw.strip().strip("\"'“”.").split()
    return " ".join(words[:MAX_WORDS]) or fallback_title(question)
