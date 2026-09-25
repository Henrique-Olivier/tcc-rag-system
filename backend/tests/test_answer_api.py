import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.answer import NOT_FOUND_ANSWER
from app.core.deps import get_llm
from app.db.models import Chunk, Citation, Document, Message
from app.llm.fake import FakeLLMProvider
from tests.fakes import ask as _ask
from tests.fakes import sse_events as _events
from tests.fakes import unit_vector

pytestmark = pytest.mark.integration


@pytest.fixture
def llm(client) -> FakeLLMProvider:
    return client.app.state.test_llm


@pytest.fixture
def indexed(db_session) -> Chunk:
    """Um documento pronto com um trecho idêntico ao vetor que o embedding falso devolve."""
    doc = Document(filename="gatos.pdf", file_hash="g" * 64, file_path="x", status="ready")
    db_session.add(doc)
    db_session.flush()
    chunk = Chunk(document_id=doc.id, page_number=5, chunk_index=0, content="Meloxicam é seguro em felinos.",
                  token_count=5, embedding=unit_vector(1.0))
    db_session.add(chunk)
    db_session.commit()
    return chunk


def test_closed_conversation_gets_409_and_nothing_is_saved(client, db_session):
    first = client.post("/conversations").json()["id"]
    client.post("/conversations")

    response = _ask(client, first, "Pergunta")

    assert response.status_code == 409
    assert db_session.scalars(select(Message)).all() == []


def test_answer_streams_events_in_order_and_saves_citations(client, db_session, llm, indexed):
    llm.response = "É seguro em gatos [1], mas ver [5]."
    conversation_id = client.post("/conversations").json()["id"]

    events = _events(_ask(client, conversation_id, "Meloxicam é seguro em gatos?"))

    names = [name for name, _ in events]
    assert names[0] == "sources" and names[-1] == "done" and set(names[1:-1]) == {"token"}
    [source] = events[0][1]["sources"]
    assert (source["marker"], source["filename"], source["page_number"]) == (1, "gatos.pdf", 5)
    assert "".join(data["text"] for name, data in events if name == "token") == llm.response
    assert events[-1][1]["markers"] == [1]

    question, answer = db_session.scalars(select(Message).order_by(Message.id)).all()
    assert (question.role, answer.role, answer.content, answer.status) == ("user", "assistant", llm.response, "complete")
    [citation] = db_session.scalars(select(Citation)).all()
    assert (citation.message_id, citation.marker, citation.chunk_id) == (answer.id, 1, indexed.id)
    assert (citation.filename, citation.page_number, citation.excerpt) == ("gatos.pdf", 5, "Meloxicam é seguro em felinos.")


def test_question_is_saved_before_generation(client, db_session, indexed):
    seen: list[str] = []

    class Spy(FakeLLMProvider):
        async def stream(self, model, messages):
            with Session(db_session.get_bind()) as other:
                seen.extend(m.content for m in other.scalars(select(Message)))
            async for piece in super().stream(model, messages):
                yield piece

    client.app.dependency_overrides[get_llm] = lambda: Spy("ok [1]")
    conversation_id = client.post("/conversations").json()["id"]

    _ask(client, conversation_id, "Pergunta salva antes?")

    assert seen == ["Pergunta salva antes?"]


def test_follow_up_records_rewritten_query_with_small_model(client, db_session, llm, indexed):
    llm.response, llm.complete_response = "Resposta [1].", "Meloxicam é seguro em cães?"
    conversation_id = client.post("/conversations").json()["id"]
    _events(_ask(client, conversation_id, "Meloxicam é seguro em gatos?"))
    llm.calls.clear()

    _events(_ask(client, conversation_id, "E em cães?"))

    follow_up = db_session.scalars(select(Message).where(Message.content == "E em cães?")).one()
    assert follow_up.rewritten_query == "Meloxicam é seguro em cães?"
    assert [model for model, _ in llm.calls] == ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]


def test_not_found_answer_is_saved_complete_and_enters_history(client, db_session, llm):
    conversation_id = client.post("/conversations").json()["id"]

    events = _events(_ask(client, conversation_id, "Algo que não está nos documentos?"))

    assert events[0] == ("sources", {"sources": []})
    assert events[1] == ("token", {"text": NOT_FOUND_ANSWER})
    assert "openai/gpt-oss-120b" not in [model for model, _ in llm.calls]  # só o título usa a LLM
    answer = db_session.scalars(select(Message).where(Message.role == "assistant")).one()
    assert (answer.content, answer.status) == (NOT_FOUND_ANSWER, "complete")
    assert db_session.scalars(select(Citation)).all() == []

    llm.complete_response = "pergunta reescrita"
    llm.calls.clear()
    _events(_ask(client, conversation_id, "E outra coisa?"))
    [(_, rewrite_messages)] = llm.calls
    assert NOT_FOUND_ANSWER in rewrite_messages[1]["content"]


def test_unknown_conversation_is_404_and_empty_question_422(client):
    assert _ask(client, 999, "Pergunta").status_code == 404
    conversation_id = client.post("/conversations").json()["id"]
    assert _ask(client, conversation_id, "").status_code == 422


def test_wide_bracket_citations_are_saved_as_plain_markers(client, db_session, llm, indexed):
    llm.response = "Dose de 0,3 mg/kg【1】."
    conversation_id = client.post("/conversations").json()["id"]

    events = _events(_ask(client, conversation_id, "Qual a dose?"))

    assert "".join(data["text"] for name, data in events if name == "token") == "Dose de 0,3 mg/kg[1]."
    assert events[-1][1]["markers"] == [1]
    assert db_session.scalars(select(Citation)).one().marker == 1
