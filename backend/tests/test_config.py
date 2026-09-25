from app.core.config import Settings


def test_settings_defaults_from_plan():
    settings = Settings(_env_file=None, groq_api_key="x", database_url="postgresql+psycopg://x", data_dir="/data")

    assert settings.embedding_model == "BAAI/bge-m3"
    assert (settings.top_k, settings.chunk_size, settings.chunk_overlap) == (8, 500, 80)
    assert (settings.max_attempts, settings.max_upload_mb) == (3, 50)
    assert (settings.api_torch_threads, settings.worker_torch_threads) == (2, 4)
