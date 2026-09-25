from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api import conversations, documents
from app.core.config import get_settings
from app.core.deps import get_embedder_loader, get_session
from app.embeddings.model import EmbedderLoader
from app.worker.heartbeat import worker_is_alive


@asynccontextmanager
async def lifespan(app: FastAPI):
    # bge-m3 só para o embedding das perguntas (seção 1), com as threads da api (seção 10).
    settings = get_settings()
    get_embedder_loader().load_in_background(settings.embedding_model, settings.api_torch_threads)
    yield


app = FastAPI(title="RAG TCC", lifespan=lifespan)
app.include_router(documents.router)
app.include_router(conversations.router)


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    worker: Literal["running", "stopped", "unknown"]
    embedding_model: Literal["ready", "loading", "failed"]


@app.get("/health", response_model=HealthOut)
def health(
    session: Annotated[Session, Depends(get_session)],
    loader: Annotated[EmbedderLoader, Depends(get_embedder_loader)],
) -> HealthOut:
    """Sempre 200; o front decide o que mostrar (seção 5.5)."""
    try:
        worker = "running" if worker_is_alive(session) else "stopped"
        database = "ok"
    except OperationalError:
        worker, database = "unknown", "unavailable"
    ok = database == "ok" and worker == "running" and loader.status == "ready"
    return HealthOut(status="ok" if ok else "degraded", database=database, worker=worker, embedding_model=loader.status)
