import asyncio

from app.chat.history import HistoryTurn
from app.chat.rewrite import rewrite_question
from app.llm.fake import FakeLLMProvider


def test_without_history_llm_is_not_called():
    fake = FakeLLMProvider("não deveria ser usado")

    assert asyncio.run(rewrite_question(fake, "pequeno", "Qual a dose em gatos?", history=[])) is None
    assert fake.calls == []


def test_with_history_returns_rewritten_question_from_small_model():
    fake = FakeLLMProvider("  Qual a dose de meloxicam em cães?\n")
    history = [HistoryTurn("Qual a dose de meloxicam em gatos?", "0,05 mg/kg (a.pdf, p. 2)")]

    rewritten = asyncio.run(rewrite_question(fake, "pequeno", "E em cães?", history))

    assert rewritten == "Qual a dose de meloxicam em cães?"
    [(model, messages)] = fake.calls
    assert model == "pequeno"
    assert "Qual a dose de meloxicam em gatos?" in messages[1]["content"]
    assert messages[1]["content"].endswith("Última pergunta: E em cães?")
