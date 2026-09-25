import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError

from app.db.models import Chunk, Citation, Conversation, Document, Message

pytestmark = pytest.mark.integration

TABLES = {"documents", "chunks", "conversations", "messages", "citations", "worker_heartbeat"}


def _document(file_hash: str = "a" * 64) -> Document:
    return Document(filename="artigo.pdf", file_hash=file_hash, file_path=f"/data/{file_hash}.pdf")


def test_migrations_downgrade_and_upgrade(test_db_url, alembic_cfg):
    engine = create_engine(test_db_url)

    command.downgrade(alembic_cfg, "base")
    assert TABLES.isdisjoint(inspect(engine).get_table_names())

    command.upgrade(alembic_cfg, "head")
    assert TABLES <= set(inspect(engine).get_table_names())
    engine.dispose()


def test_file_hash_is_unique(db_session):
    db_session.add(_document())
    db_session.commit()

    db_session.add(_document())
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_deleting_conversation_cascades_to_messages_and_citations(db_session):
    document = _document()
    db_session.add(document)
    db_session.flush()
    chunk = Chunk(document_id=document.id, page_number=1, chunk_index=0, content="texto", token_count=1, embedding=[0.0] * 1024)
    conversation = Conversation()
    db_session.add_all([chunk, conversation])
    db_session.flush()
    message = Message(conversation_id=conversation.id, role="assistant", content="resposta [1]")
    db_session.add(message)
    db_session.flush()
    db_session.add(Citation(message_id=message.id, chunk_id=chunk.id, document_id=document.id, marker=1,
                            filename="artigo.pdf", page_number=1, excerpt="texto"))
    db_session.commit()

    db_session.delete(conversation)
    db_session.commit()

    assert db_session.scalars(select(Message)).all() == []
    assert db_session.scalars(select(Citation)).all() == []
    assert db_session.get(Chunk, chunk.id) is not None
