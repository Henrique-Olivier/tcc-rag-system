import time
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.main import app
from app.core.deps import get_session
from app.db.models import WorkerHeartbeat
from app.worker.heartbeat import start_heartbeat

pytestmark = pytest.mark.integration


def _last_seen(session) -> datetime:
    session.expire_all()
    return session.scalar(select(WorkerHeartbeat.last_seen_at))


def test_heartbeat_keeps_beating_during_long_processing(engine, db_session):
    stop = start_heartbeat(sessionmaker(engine), interval=0.1)
    try:
        time.sleep(0.3)  # "processamento longo" na thread principal
        first = _last_seen(db_session)
        time.sleep(0.3)
        assert _last_seen(db_session) > first
    finally:
        stop.set()
        time.sleep(0.15)  # deixa a thread terminar antes da limpeza das tabelas


def test_health_reports_worker_running_or_stopped(client, db_session):
    assert client.get("/health").json() == {"status": "degraded", "database": "ok", "worker": "stopped"}

    db_session.add(WorkerHeartbeat(id=1, last_seen_at=datetime.now(UTC) - timedelta(seconds=90)))
    db_session.commit()
    assert client.get("/health").json()["worker"] == "stopped"

    db_session.get(WorkerHeartbeat, 1).last_seen_at = datetime.now(UTC)
    db_session.commit()
    assert client.get("/health").json() == {"status": "ok", "database": "ok", "worker": "running"}


def test_health_reports_database_down(client):
    dead = create_engine("postgresql+psycopg://x:y@127.0.0.1:1/nada", connect_args={"connect_timeout": 2})
    app.dependency_overrides[get_session] = lambda: Session(dead)

    assert client.get("/health").json() == {"status": "degraded", "database": "unavailable", "worker": "unknown"}
