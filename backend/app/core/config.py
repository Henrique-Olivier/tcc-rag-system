"""Variáveis de ambiente do plano, seção 10. Sem padrão = obrigatória no .env."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env da raiz, rodando a partir de backend/; no Compose as variáveis vêm do env_file.
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    groq_api_key: SecretStr
    llm_answer_model: str = "llama-3.3-70b-versatile"
    llm_rewrite_model: str = "llama-3.1-8b-instant"
    embedding_model: str = "BAAI/bge-m3"
    top_k: int = 8
    chunk_size: int = 500
    chunk_overlap: int = 80
    # Provisório: recalibrar com o conjunto de avaliação (seção 6.3).
    min_similarity: float = 0.3
    history_turns: int = 3
    max_attempts: int = 3
    max_upload_mb: int = 50
    api_torch_threads: int = 2
    worker_torch_threads: int = 4
    database_url: str
    data_dir: Path


def get_settings() -> Settings:
    return Settings()
