"""Fixtures de integração: banco `rag_test` no Postgres do Compose (plano, seção 12).

Nunca usa o banco da aplicação, porque as tabelas são limpas a cada teste.
Sem Postgres acessível, os testes de integração são pulados.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, Engine, create_engine, make_url, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.models import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]


class _TestDbEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR.parent / ".env", extra="ignore")

    postgres_user: str = "rag"
    postgres_password: str = ""
    test_database_url: str | None = None


def _test_database_url() -> URL:
    env = _TestDbEnv()
    if env.test_database_url:
        return make_url(env.test_database_url)
    # 127.0.0.1 e não localhost: no Windows, localhost tenta IPv6 e trava.
    return URL.create("postgresql+psycopg", env.postgres_user, env.postgres_password, "127.0.0.1", 5432, "rag_test")


def _alembic_config(url: URL) -> Config:
    config = Config(BACKEND_DIR / "alembic.ini")
    # ConfigParser interpreta %; a senha pode conter o caractere.
    config.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def test_db_url() -> URL:
    url = _test_database_url()
    try:
        admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5})
        with admin.connect() as conn:
            if not conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}):
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
        admin.dispose()
    except OperationalError as exc:
        pytest.skip(f"Postgres de teste indisponível ({exc.orig}); suba o `db` com docker compose")
    command.upgrade(_alembic_config(url), "head")
    return url


@pytest.fixture
def alembic_cfg(test_db_url: URL) -> Config:
    return _alembic_config(test_db_url)


@pytest.fixture(scope="session")
def engine(test_db_url: URL) -> Engine:
    return create_engine(test_db_url)


@pytest.fixture
def db_session(engine: Engine):
    with Session(engine, expire_on_commit=False) as session:
        yield session
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
