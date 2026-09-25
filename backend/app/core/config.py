"""Variáveis de ambiente do plano, seção 10. Sem padrão = obrigatória no .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env da raiz, rodando a partir de backend/; no Compose as variáveis vêm do env_file.
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    groq_api_key: SecretStr
    llm_answer_model: str = "openai/gpt-oss-120b"
    llm_rewrite_model: str = "openai/gpt-oss-20b"
    embedding_model: str = "BAAI/bge-m3"
    # Calibrados na T35 (measurements.md, seção 6.3); mudar o chunking exige reindexar (seção 5.6).
    top_k: int = 12
    chunk_size: int = 300
    chunk_overlap: int = 50
    # Calibrado na T26 com o conjunto de avaliação (measurements.md, seção 6.3).
    min_similarity: float = 0.5
    history_turns: int = 3
    max_attempts: int = 3
    max_upload_mb: int = 50
    api_torch_threads: int = 2
    worker_torch_threads: int = 4
    database_url: str
    data_dir: Path


@lru_cache
def get_settings() -> Settings:
    return Settings()
