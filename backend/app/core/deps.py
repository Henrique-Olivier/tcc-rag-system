from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

from app.db.session import get_sessionmaker
from app.embeddings.model import EmbedderLoader
from app.llm.provider import GroqProvider, LLMProvider

# Único por processo da api (seção 1: um worker do uvicorn).
_embedder_loader = EmbedderLoader()


def get_session() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição."""
    with get_sessionmaker()() as session:
        yield session


def get_embedder_loader() -> EmbedderLoader:
    return _embedder_loader


def get_session_factory() -> sessionmaker[Session]:
    """Para quem precisa de sessão própria, como o streaming, que dura mais que a requisição."""
    return get_sessionmaker()


@lru_cache
def get_llm() -> LLMProvider:
    return GroqProvider(get_settings().groq_api_key.get_secret_value())
