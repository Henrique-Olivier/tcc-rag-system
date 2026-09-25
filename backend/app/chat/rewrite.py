"""Reescrita da pergunta com o histórico (plano, seção 6, etapa 1)."""

from app.chat.history import HistoryTurn
from app.chat.prompt import format_history
from app.llm.provider import LLMProvider

REWRITE_INSTRUCTIONS = """\
Reescreva a última pergunta da estudante como uma pergunta independente, que possa ser entendida sem o histórico. \
Use o histórico apenas para resolver referências como "e em cães?" ou "qual a dose dele?". \
Mantenha o português e o sentido original. Responda somente com a pergunta reescrita, sem explicações."""


async def rewrite_question(llm: LLMProvider, model: str, question: str, history: list[HistoryTurn]) -> str | None:
    """Sem histórico não há o que resolver: devolve None e a pergunta original segue direto (CA11)."""
    if not history:
        return None
    user = f"<historico>\n{format_history(history)}\n</historico>\n\nÚltima pergunta: {question}"
    rewritten = await llm.complete(model, [{"role": "system", "content": REWRITE_INSTRUCTIONS}, {"role": "user", "content": user}])
    return rewritten.strip() or question
