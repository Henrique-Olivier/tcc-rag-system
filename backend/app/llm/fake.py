import re
from collections.abc import AsyncIterator

from app.llm.provider import ChatMessage


class FakeLLMProvider:
    """Respostas fixas para os testes (seção 10). Registra as chamadas recebidas."""

    def __init__(self, response: str = "resposta de teste") -> None:
        self.response = response
        self.calls: list[tuple[str, list[ChatMessage]]] = []

    async def complete(self, model: str, messages: list[ChatMessage]) -> str:
        self.calls.append((model, messages))
        return self.response

    async def stream(self, model: str, messages: list[ChatMessage]) -> AsyncIterator[str]:
        self.calls.append((model, messages))
        for piece in re.findall(r"\S+\s*", self.response):
            yield piece
