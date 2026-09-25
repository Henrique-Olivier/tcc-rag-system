from typing import Annotated, Literal

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api import documents
from app.core.deps import get_session
from app.worker.heartbeat import worker_is_alive

app = FastAPI(title="RAG TCC")
app.include_router(documents.router)


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    worker: Literal["running", "stopped", "unknown"]


@app.get("/health", response_model=HealthOut)
def health(session: Annotated[Session, Depends(get_session)]) -> HealthOut:
    """Sempre 200; o front decide o que mostrar (seção 5.5). O modelo de embedding entra na T12."""
    try:
        worker = "running" if worker_is_alive(session) else "stopped"
        database = "ok"
    except OperationalError:
        worker, database = "unknown", "unavailable"
    status = "ok" if database == "ok" and worker == "running" else "degraded"
    return HealthOut(status=status, database=database, worker=worker)
