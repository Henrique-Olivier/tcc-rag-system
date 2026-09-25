from fastapi import FastAPI

app = FastAPI(title="RAG TCC")


@app.get("/health")
def health() -> dict[str, str]:
    # Versão mínima; banco, modelo e heartbeat do worker entram depois (seções 5.5 e 8).
    return {"status": "ok"}
