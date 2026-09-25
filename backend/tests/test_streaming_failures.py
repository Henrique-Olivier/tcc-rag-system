import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.answer import ERROR_MESSAGE, RATE_LIMIT_MESSAGE, AnswerConfig, answer_question
from app.core.deps import get_llm
from app.db.models import Chunk, Conversation, Document, Message
from app.llm.fake import FakeLLMProvider
from app.llm.provider import LLMRateLimitError
from tests.fakes import FakeEmbedder, unit_vector
from tests.fakes import ask as _ask
from tests.fakes import sse_events as _events

pytestmark = pytest.mark.integration

CONFIG = AnswerConfig("grande", "pequeno", top_k=8, min_similarity=0.3, history_turns=3)


class BrokenLLM(FakeLLMProvider):
    """Transmite um pedaço e depois falha, ou falha logo com o erro dado."""

    def __init__(self, error: Exception, after_first: bool = True) -> None:
        super().__init__("parcial que não pode ser salva")
        self.error, self.after_first = error, after_first

    async def stream(self, model, messages):
        if self.after_first:
            yield "parcial "
        raise self.error


class SlowLLM(FakeLLMProvider):
    async def stream(self, model, messages):
        yield "começo "
        await asyncio.sleep(30)
        yield "nunca chega"


@pytest.fixture
def conversation(db_session) -> int:
    doc = Document(filename="gatos.pdf", file_hash="g" * 64, file_path="x", status="ready")
    conversation = Conversation()
    db_session.add_all([doc, conversation])
    db_session.flush()
    db_session.add(Chunk(document_id=doc.id, page_number=1, chunk_index=0, content="Meloxicam em gatos.",
                         token_count=3, embedding=unit_vector(1.0)))
    db_session.commit()
    return conversation.id


def _messages(db_session) -> list[tuple[str, str, str]]:
    db_session.expire_all()
    return [(m.role, m.status, m.content) for m in db_session.scalars(select(Message).order_by(Message.id))]


def test_provider_error_mid_answer_saves_error_without_content(client, db_session, conversation):
    client.app.dependency_overrides[get_llm] = lambda: BrokenLLM(RuntimeError("queda do provedor"))

    events = _events(_ask(client, conversation, "Pergunta"))

    assert [name for name, _ in events] == ["sources", "token", "error"]
    assert events[-1][1] == {"message": ERROR_MESSAGE}
    assert _messages(db_session) == [("user", "complete", "Pergunta"), ("assistant", "error", "")]


def test_rate_limit_becomes_error_event_with_limit_message(client, db_session, conversation):
    client.app.dependency_overrides[get_llm] = lambda: BrokenLLM(LLMRateLimitError("429"), after_first=False)

    events = _events(_ask(client, conversation, "Pergunta"))

    assert events[-1] == ("error", {"message": RATE_LIMIT_MESSAGE})
    assert _messages(db_session)[-1] == ("assistant", "error", "")


def test_client_disconnect_saves_error(engine, db_session, conversation):
    async def disconnect_after_first_token():
        with Session(engine) as session:
            events = answer_question(session, SlowLLM(), FakeEmbedder(), CONFIG, conversation, "Pergunta")
            async for event in events:
                if event.name == "token":
                    break
            await events.aclose()  # o que a rota faz ao detectar a desconexão

    asyncio.run(disconnect_after_first_token())

    assert _messages(db_session) == [("user", "complete", "Pergunta"), ("assistant", "error", "")]


def test_cancelled_generation_still_saves_error(engine, db_session, conversation):
    async def cancel_while_waiting_provider():
        started = asyncio.Event()

        async def consume():
            with Session(engine) as session:
                async for event in answer_question(session, SlowLLM(), FakeEmbedder(), CONFIG, conversation, "Pergunta"):
                    if event.name == "token":
                        started.set()

        task = asyncio.create_task(consume())
        await started.wait()
        task.cancel()  # o Starlette cancela o gerador quando o cliente cai
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel_while_waiting_provider())

    assert _messages(db_session)[-1] == ("assistant", "error", "")
