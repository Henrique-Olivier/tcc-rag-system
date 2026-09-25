"""Interface LLMProvider e implementação Groq (plano, seções 2 e 10)."""

from collections.abc import AsyncIterator
from typing import Protocol

import openai
from openai import AsyncOpenAI

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

ChatMessage = dict[str, str]  # {"role": "system" | "user" | "assistant", "content": ...}


class LLMRateLimitError(Exception):
    """Limite de requisições ou tokens do provedor atingido (seção 6.7)."""


class LLMProvider(Protocol):
    async def complete(self, model: str, messages: list[ChatMessage]) -> str: ...

    def stream(self, model: str, messages: list[ChatMessage]) -> AsyncIterator[str]: ...


class GroqProvider:
    """Groq pela API compatível com a OpenAI; trocar de provedor é trocar a URL."""

    def __init__(self, api_key: str, client: AsyncOpenAI | None = None) -> None:
        self._client = client or AsyncOpenAI(api_key=api_key, base_url=GROQ_BASE_URL)

    async def complete(self, model: str, messages: list[ChatMessage]) -> str:
        try:
            response = await self._client.chat.completions.create(model=model, messages=messages)
        except openai.RateLimitError as exc:
            raise LLMRateLimitError(str(exc)) from exc
        return response.choices[0].message.content or ""

    async def stream(self, model: str, messages: list[ChatMessage]) -> AsyncIterator[str]:
        try:
            chunks = await self._client.chat.completions.create(model=model, messages=messages, stream=True)
            async for chunk in chunks:
                text = chunk.choices[0].delta.content if chunk.choices else None
                if text:
                    yield text
        except openai.RateLimitError as exc:
            raise LLMRateLimitError(str(exc)) from exc
