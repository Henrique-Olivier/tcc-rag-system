"""Entrypoint do worker: `python -m app.worker` (plano, seções 1 e 5.2)."""

import logging
import time

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.embeddings.model import Embedder
from app.worker.queue import recover_interrupted, run_once

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("worker")

IDLE_SECONDS = 5


def main() -> None:
    settings = get_settings()
    embedder = Embedder(settings.embedding_model, settings.worker_torch_threads)
    sessions = get_sessionmaker()
    with sessions() as session:
        recover_interrupted(session, settings.max_attempts)
    log.info("worker iniciado")
    while True:
        try:
            if not run_once(sessions, embedder, settings.chunk_size, settings.chunk_overlap):
                time.sleep(IDLE_SECONDS)
        except Exception:  # banco fora do ar, por exemplo: espera e tenta de novo
            log.exception("erro no loop do worker")
            time.sleep(IDLE_SECONDS)


if __name__ == "__main__":
    main()
