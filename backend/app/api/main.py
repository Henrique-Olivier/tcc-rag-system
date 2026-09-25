from fastapi import FastAPI

from app.api import documents

app = FastAPI(title="RAG TCC")
app.include_router(documents.router)


@app.get("/health")
def health() -> dict[str, str]:
    # Versão mínima; banco e worker entram na T10, modelo de embedding na T12.
    return {"status": "ok"}
