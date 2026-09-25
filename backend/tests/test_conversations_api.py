from datetime import UTC, datetime

import pytest

from app.chat.conversations import ConversationState, conversation_state
from app.db.models import Chunk, Citation, Conversation, Document, Message
from tests.fakes import unit_vector

pytestmark = pytest.mark.integration


def _add_message(session, conversation_id: int, role: str = "user", content: str = "Pergunta") -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    session.add(message)
    session.commit()
    return message


def test_creating_conversation_closes_previous(client, db_session):
    first = client.post("/conversations").json()
    second = client.post("/conversations").json()

    assert second["closed_at"] is None
    assert db_session.get(Conversation, first["id"]).closed_at is not None


def test_close_open_closes_all(client, db_session):
    db_session.add_all([Conversation(), Conversation()])
    db_session.commit()

    assert client.post("/conversations/close-open").status_code == 204
    assert all(c.closed_at is not None for c in db_session.query(Conversation))


def test_list_hides_empty_conversations(client, db_session):
    empty = client.post("/conversations").json()
    used = client.post("/conversations").json()
    _add_message(db_session, used["id"])

    listed = client.get("/conversations").json()

    assert [c["id"] for c in listed] == [used["id"]]
    assert empty["id"] not in [c["id"] for c in listed]


def test_detail_keeps_excerpt_and_flags_removed_document(client, db_session):
    doc = Document(filename="velho.pdf", file_hash="v" * 64, file_path="x", status="ready")
    db_session.add(doc)
    db_session.flush()
    chunk = Chunk(document_id=doc.id, page_number=4, chunk_index=0, content="trecho", token_count=1, embedding=unit_vector(1.0))
    db_session.add(chunk)
    db_session.commit()
    conversation_id = client.post("/conversations").json()["id"]
    _add_message(db_session, conversation_id, "user", "Pergunta")
    answer = _add_message(db_session, conversation_id, "assistant", "Resposta [1].")
    db_session.add(Citation(message_id=answer.id, chunk_id=chunk.id, document_id=doc.id, marker=1,
                            filename="velho.pdf", page_number=4, excerpt="trecho copiado"))
    doc.deleted_at = datetime.now(UTC)
    db_session.commit()

    detail = client.get(f"/conversations/{conversation_id}").json()

    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    [citation] = detail["messages"][1]["citations"]
    assert citation == {"marker": 1, "document_id": doc.id, "chunk_id": chunk.id, "filename": "velho.pdf",
                        "page_number": 4, "excerpt": "trecho copiado", "document_removed": True}


def test_delete_removes_messages_and_citations(client, db_session):
    conversation_id = client.post("/conversations").json()["id"]
    _add_message(db_session, conversation_id)

    assert client.delete(f"/conversations/{conversation_id}").status_code == 204
    assert db_session.query(Message).count() == 0
    assert client.get(f"/conversations/{conversation_id}").status_code == 404
    assert client.delete(f"/conversations/{conversation_id}").status_code == 404


def test_conversation_state_distinguishes_open_closed_and_missing(client, db_session):
    first = client.post("/conversations").json()["id"]
    second = client.post("/conversations").json()["id"]

    assert conversation_state(db_session, second) == ConversationState.OPEN
    assert conversation_state(db_session, first) == ConversationState.CLOSED
    assert conversation_state(db_session, 999) == ConversationState.NOT_FOUND


def test_citation_survives_when_its_chunk_is_replaced(client, db_session):
    doc = Document(filename="artigo.pdf", file_hash="r" * 64, file_path="x", status="ready")
    db_session.add(doc)
    db_session.flush()
    chunk = Chunk(document_id=doc.id, page_number=2, chunk_index=0, content="trecho", token_count=1, embedding=unit_vector(1.0))
    db_session.add(chunk)
    db_session.commit()
    conversation_id = client.post("/conversations").json()["id"]
    answer = _add_message(db_session, conversation_id, "assistant", "Resposta [1].")
    db_session.add(Citation(message_id=answer.id, chunk_id=chunk.id, document_id=doc.id, marker=1,
                            filename="artigo.pdf", page_number=2, excerpt="trecho copiado"))
    db_session.commit()

    db_session.delete(chunk)  # o que a reindexação faz (seção 5.6)
    db_session.commit()

    [citation] = client.get(f"/conversations/{conversation_id}").json()["messages"][0]["citations"]
    assert (citation["chunk_id"], citation["excerpt"], citation["page_number"]) == (None, "trecho copiado", 2)
