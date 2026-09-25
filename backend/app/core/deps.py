from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db.session import get_sessionmaker
from app.embeddings.model import EmbedderLoader

# Único por processo da api (seção 1: um worker do uvicorn).
_embedder_loader = EmbedderLoader()


def get_session() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição."""
    with get_sessionmaker()() as session:
        yield session


def get_embedder_loader() -> EmbedderLoader:
    return _embedder_loader
