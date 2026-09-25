"""Heartbeat do worker (plano, seção 5.5)."""

import logging
import threading
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import WorkerHeartbeat

log = logging.getLogger("worker")

INTERVAL_SECONDS = 10
STALE_AFTER = timedelta(seconds=60)


def beat(session: Session) -> None:
    stmt = insert(WorkerHeartbeat).values(id=1, last_seen_at=func.now())
    session.execute(stmt.on_conflict_do_update(index_elements=["id"], set_={"last_seen_at": func.now()}))
    session.commit()


def start_heartbeat(sessions: sessionmaker[Session], interval: float = INTERVAL_SECONDS) -> threading.Event:
    """Thread própria: continua batendo durante um documento longo. Devolve o evento que a para."""
    stop = threading.Event()

    def loop() -> None:
        while not stop.is_set():
            try:
                with sessions() as session:
                    beat(session)
            except Exception:
                log.exception("falha ao gravar o heartbeat")
            stop.wait(interval)

    threading.Thread(target=loop, name="heartbeat", daemon=True).start()
    return stop


def worker_is_alive(session: Session) -> bool:
    """Compara com o relógio do banco, não com o do container da api."""
    return bool(session.scalar(select(WorkerHeartbeat.last_seen_at > func.now() - STALE_AFTER)))
