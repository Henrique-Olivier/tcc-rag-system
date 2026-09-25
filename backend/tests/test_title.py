import asyncio

import pytest

from app.chat.title import fallback_title, generate_title
from app.db.models import Conversation
from app.llm.fake import FakeLLMProvider
from tests.fakes import ask, sse_events

LONG = "Quais estudos avaliaram o uso de meloxicam por via oral em gatos idosos com doença renal crônica?"


class FailingLLM(FakeLLMProvider):
    async def complete(self, model, messages):
        raise RuntimeError("provedor fora")


def test_fallback_is_truncated_question_without_cutting_words():
    assert fallback_title("Dose de meloxicam?") == "Dose de meloxicam?"
    assert fallback_title(LONG) == "Quais estudos avaliaram o uso de meloxicam por via oral em…"


def test_generated_title_has_at_most_six_words_without_quotes():
    fake = FakeLLMProvider(complete_response='"Meloxicam oral em gatos idosos com doença renal".')

    assert asyncio.run(generate_title(fake, "pequeno", LONG)) == "Meloxicam oral em gatos idosos com"


def test_provider_failure_uses_truncated_question():
    assert asyncio.run(generate_title(FailingLLM(), "pequeno", LONG)) == fallback_title(LONG)


@pytest.mark.integration
def test_title_is_set_after_first_answer_only(client, db_session):
    llm = client.app.state.test_llm
    llm.complete_response = "Meloxicam em gatos"
    conversation_id = client.post("/conversations").json()["id"]

    sse_events(ask(client, conversation_id, "Meloxicam é seguro em gatos?"))
    db_session.expire_all()
    assert db_session.get(Conversation, conversation_id).title == "Meloxicam em gatos"

    llm.complete_response = "Outro título"
    sse_events(ask(client, conversation_id, "E em cães?"))
    db_session.expire_all()
    assert db_session.get(Conversation, conversation_id).title == "Meloxicam em gatos"
