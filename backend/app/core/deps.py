from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db.session import get_sessionmaker


def get_session() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição."""
    with get_sessionmaker()() as session:
        yield session
