from datetime import UTC, datetime

import pytest

from app.chat.history import HistoryTurn, PastCitation, PastMessage, load_messages, prepare_history
from app.db.models import Chunk, Citation, Conversation, Document, Message
from tests.fakes import unit_vector

NOT_FOUND = "Não encontrei informação suficiente nos documentos para responder."


def _answer(content: str, *citations: PastCitation, status: str = "complete") -> PastMessage:
    return PastMessage("assistant", content, status, list(citations))


def test_markers_become_textual_references():
    messages = [
        PastMessage("user", "Qual a dose?"),
        _answer("A dose é 0,1 mg/kg [1], segura em idosos [2, 3]. Ver [9].",
                PastCitation(1, "a.pdf", 4, False), PastCitation(2, "b.pdf", 7, False), PastCitation(3, "a.pdf", 5, False)),
    ]

    assert prepare_history(messages, turns=3) == [
        HistoryTurn("Qual a dose?", "A dose é 0,1 mg/kg (a.pdf, p. 4), segura em idosos (b.pdf, p. 7; a.pdf, p. 5). Ver .")
    ]


def test_answer_citing_removed_document_is_omitted_but_question_kept():
    messages = [PastMessage("user", "E em cães?"), _answer("Sim [1].", PastCitation(1, "x.pdf", 1, True))]

    assert prepare_history(messages, turns=3) == [HistoryTurn("E em cães?", None)]


def test_error_answer_is_omitted():
    messages = [PastMessage("user", "Pergunta"), _answer("", status="error")]

    assert prepare_history(messages, turns=3) == [HistoryTurn("Pergunta", None)]


def test_only_last_turns_are_kept_and_not_found_answer_stays():
    messages = []
    for i in range(4):
        messages += [PastMessage("user", f"p{i}"), _answer(NOT_FOUND if i == 3 else f"r{i}")]

    assert prepare_history(messages, turns=2) == [HistoryTurn("p2", "r2"), HistoryTurn("p3", NOT_FOUND)]
    assert prepare_history(messages, turns=0) == []


@pytest.mark.integration
def test_load_messages_flags_removed_documents(db_session):
    removed = Document(filename="velho.pdf", file_hash="v" * 64, file_path="x", status="ready", deleted_at=datetime.now(UTC))
    conversation = Conversation()
    db_session.add_all([removed, conversation])
    db_session.flush()
    chunk = Chunk(document_id=removed.id, page_number=2, chunk_index=0, content="c", token_count=1, embedding=unit_vector(1.0))
    question = Message(conversation_id=conversation.id, role="user", content="Pergunta")
    db_session.add_all([chunk, question])
    db_session.flush()
    answer = Message(conversation_id=conversation.id, role="assistant", content="Resposta [1].")
    current = Message(conversation_id=conversation.id, role="user", content="Pergunta atual")
    db_session.add_all([answer, current])
    db_session.flush()
    db_session.add(Citation(message_id=answer.id, chunk_id=chunk.id, document_id=removed.id, marker=1,
                            filename="velho.pdf", page_number=2, excerpt="c"))
    db_session.commit()

    messages = load_messages(db_session, conversation.id, before_message_id=current.id)

    assert [m.content for m in messages] == ["Pergunta", "Resposta [1]."]
    assert messages[1].citations == [PastCitation(1, "velho.pdf", 2, True)]
