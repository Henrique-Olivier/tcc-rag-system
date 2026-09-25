"""Pipeline de consulta: pergunta -> eventos de resposta (plano, seções 6 e 6.5). Sem FastAPI."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.chat.history import load_messages, prepare_history
from app.chat.markers import parse_markers
from app.chat.prompt import build_answer_messages
from app.chat.rewrite import rewrite_question
from app.db.models import Citation, Message
from app.llm.provider import LLMProvider
from app.retrieval.search import RetrievedChunk, search

NOT_FOUND_ANSWER = "Não encontrei informação suficiente nos documentos enviados para responder a essa pergunta."


@dataclass(frozen=True)
class AnswerConfig:
    answer_model: str
    rewrite_model: str
    top_k: int
    min_similarity: float
    history_turns: int


@dataclass(frozen=True)
class Event:
    name: str  # sources | token | done | error
    data: dict[str, Any]


def _source_payload(number: int, source: RetrievedChunk) -> dict[str, Any]:
    return {"marker": number, "chunk_id": source.chunk_id, "document_id": source.document_id,
            "filename": source.filename, "page_number": source.page_number, "excerpt": source.content}


async def answer_question(
    session: Session, llm: LLMProvider, embedder, config: AnswerConfig, conversation_id: int, question: str
) -> AsyncIterator[Event]:
    # 1. A pergunta é salva antes de qualquer outra coisa (CA12).
    user_message = await asyncio.to_thread(_save_message, session, conversation_id, "user", question)
    past = await asyncio.to_thread(load_messages, session, conversation_id, user_message.id)
    history = prepare_history(past, config.history_turns)

    rewritten = await rewrite_question(llm, config.rewrite_model, question, history)
    if rewritten:
        user_message.rewritten_query = rewritten
        await asyncio.to_thread(session.commit)

    # 2 e 3. Busca com a pergunta reescrita (ou original) e filtro de relevância.
    [vector] = await asyncio.to_thread(embedder.encode, [rewritten or question])
    sources = await asyncio.to_thread(search, session, vector, config.top_k, config.min_similarity)
    yield Event("sources", {"sources": [_source_payload(n, s) for n, s in enumerate(sources, start=1)]})

    if not sources:  # sem chamar a LLM; resposta salva e usada no histórico (CA08)
        answer = await asyncio.to_thread(_save_message, session, conversation_id, "assistant", NOT_FOUND_ANSWER)
        yield Event("token", {"text": NOT_FOUND_ANSWER})
        yield Event("done", {"message_id": answer.id, "markers": []})
        return

    # 4 e 5. Prompt e geração em streaming.
    pieces: list[str] = []
    async for piece in llm.stream(config.answer_model, build_answer_messages(question, sources, history)):
        pieces.append(piece)
        yield Event("token", {"text": piece})

    # 6. Citações: uma por marcador válido, com cópia do trecho e do nome do arquivo (CA07, CA16).
    text = "".join(pieces)
    markers = parse_markers(text, len(sources))
    answer = await asyncio.to_thread(_save_answer, session, conversation_id, text, [(m, sources[m - 1]) for m in markers])
    yield Event("done", {"message_id": answer.id, "markers": markers})


def _save_message(session: Session, conversation_id: int, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    session.add(message)
    session.commit()
    return message


def _save_answer(session: Session, conversation_id: int, content: str, cited: list[tuple[int, RetrievedChunk]]) -> Message:
    message = Message(conversation_id=conversation_id, role="assistant", content=content)
    session.add(message)
    session.flush()
    session.add_all(
        Citation(message_id=message.id, chunk_id=s.chunk_id, document_id=s.document_id, marker=marker,
                 filename=s.filename, page_number=s.page_number, excerpt=s.content)
        for marker, s in cited
    )
    session.commit()
    return message

