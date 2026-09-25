import asyncio
from types import SimpleNamespace

import httpx
import openai
import pytest

from app.llm.fake import FakeLLMProvider
from app.llm.provider import GroqProvider, LLMRateLimitError

MESSAGES = [{"role": "user", "content": "pergunta"}]


async def _collect(stream) -> list[str]:
    return [piece async for piece in stream]


def _rate_limit_error() -> openai.RateLimitError:
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com"))
    return openai.RateLimitError("limite atingido", response=response, body=None)


class _StubClient:
    """Imita AsyncOpenAI: chat.completions.create devolve resposta, stream ou erro."""

    def __init__(self, pieces: list[str] | None = None, error: Exception | None = None) -> None:
        self.pieces, self.error = pieces or [], error
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, model, messages, stream=False):
        if self.error:
            raise self.error
        if not stream:
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="".join(self.pieces)))])
        return self._chunks()

    async def _chunks(self):
        for piece in self.pieces:
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=piece))])
        yield SimpleNamespace(choices=[])  # último chunk do Groq vem sem choices


def test_fake_provider_completes_and_streams_configured_response():
    fake = FakeLLMProvider("Os gatos [1] toleram bem.")

    assert asyncio.run(fake.complete("m", MESSAGES)) == "Os gatos [1] toleram bem."
    assert "".join(asyncio.run(_collect(fake.stream("m", MESSAGES)))) == "Os gatos [1] toleram bem."
    assert [model for model, _ in fake.calls] == ["m", "m"]


def test_groq_streams_pieces_in_order():
    provider = GroqProvider("chave", client=_StubClient(["Olá", ", ", "mundo"]))

    assert asyncio.run(_collect(provider.stream("m", MESSAGES))) == ["Olá", ", ", "mundo"]
    assert asyncio.run(provider.complete("m", MESSAGES)) == "Olá, mundo"


def test_groq_rate_limit_becomes_own_exception():
    provider = GroqProvider("chave", client=_StubClient(error=_rate_limit_error()))

    with pytest.raises(LLMRateLimitError):
        asyncio.run(provider.complete("m", MESSAGES))
    with pytest.raises(LLMRateLimitError):
        asyncio.run(_collect(provider.stream("m", MESSAGES)))
