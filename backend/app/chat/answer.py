"""Pipeline de consulta: pergunta -> eventos de resposta (plano, seções 6 e 6.5). Sem FastAPI."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import aclosing
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.chat.history import load_messages, prepare_history
from app.chat.markers import normalize_brackets, parse_markers, strip_citation_suffixes
from app.chat.prompt import build_answer_messages
from app.chat.rewrite import rewrite_question
from app.chat.title import fallback_title, generate_title
from app.db.models import Citation, Conversation, Message
from app.llm.provider import LLMProvider, LLMRateLimitError
from app.retrieval.search import RetrievedChunk, search

log = logging.getLogger("api")

NOT_FOUND_ANSWER = "Não encontrei informação suficiente nos documentos enviados para responder a essa pergunta."
RATE_LIMIT_MESSAGE = (
    "O limite de uso do modelo foi atingido. Aguarde cerca de um minuto e tente de novo; "
    "se continuar, o limite diário pode ter acabado (seção 6.7)."
)
ERROR_MESSAGE = "Não foi possível concluir a resposta. Tente perguntar de novo."


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
            "filename": source.filename, "page_number": source.page_number, "excerpt": source.content,
            "similarity": round(source.similarity, 4)}


async def answer_question(
    session: Session, llm: LLMProvider, embedder, config: AnswerConfig, conversation_id: int, question: str
) -> AsyncIterator[Event]:
    """A pergunta fica salva antes da geração; qualquer falha grava uma resposta com status `error` (seção 6.6)."""
    # 1. A pergunta é salva antes de qualquer outra coisa (CA12).
    user_message = await asyncio.to_thread(_save_message, session, conversation_id, "user", question)
    finished = False
    try:
        async with aclosing(_answer_events(session, llm, embedder, config, conversation_id, question, user_message)) as events:
            async for event in events:
                finished = finished or event.name == "done"
                yield event
        await _title_after_first_answer(session, llm, config.rewrite_model, conversation_id, question)
    except LLMRateLimitError:
        finished = True
        _record_error(session, conversation_id)
        yield Event("error", {"message": RATE_LIMIT_MESSAGE})
    except Exception:
        log.exception("erro ao responder na conversa %s", conversation_id)
        finished = True
        _record_error(session, conversation_id)
        yield Event("error", {"message": ERROR_MESSAGE})
    finally:
        if not finished:
            # Cliente desconectou (GeneratorExit ou CancelledError). Gravação síncrona, sem await:
            # o cancelamento não tem onde interrompê-la.
            _record_error(session, conversation_id)


async def _answer_events(
    session: Session, llm: LLMProvider, embedder, config: AnswerConfig, conversation_id: int, question: str, user_message: Message
) -> AsyncIterator[Event]:
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
        yield Event("done", {"message_id": answer.id, "markers": [], "uncited": False})
        return

    # 4 e 5. Prompt e geração em streaming.
    pieces: list[str] = []
    # aclosing: se a resposta for interrompida, a chamada ao provedor é encerrada junto.
    async with aclosing(llm.stream(config.answer_model, build_answer_messages(question, sources, history))) as stream:
        async for raw in stream:
            piece = normalize_brackets(raw)
            pieces.append(piece)
            yield Event("token", {"text": piece})

    # 6. Citações: uma por marcador válido, com cópia do trecho e do nome do arquivo (CA07, CA16).
    text = strip_citation_suffixes("".join(pieces))
    markers = parse_markers(text, len(sources))
    # Conteúdo sem nenhum marcador válido: salva, mas a interface avisa (seção 6.4).
    uncited = bool(text.strip()) and not markers
    cited = [(m, sources[m - 1]) for m in markers]
    answer = await asyncio.to_thread(_save_answer, session, conversation_id, text, cited, uncited)
    yield Event("done", {"message_id": answer.id, "markers": markers, "uncited": uncited})


def _save_message(session: Session, conversation_id: int, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    session.add(message)
    session.commit()
    return message


async def _title_after_first_answer(session: Session, llm: LLMProvider, model: str, conversation_id: int, question: str) -> None:
    """Depois da primeira resposta concluída (seção 6.8). O provisório garante um título mesmo se a geração cair."""
    conversation = await asyncio.to_thread(session.get, Conversation, conversation_id)
    if conversation.title is not None:
        return
    conversation.title = fallback_title(question)
    await asyncio.to_thread(session.commit)
    conversation.title = await generate_title(llm, model, question)
    await asyncio.to_thread(session.commit)


def _record_error(session: Session, conversation_id: int) -> None:
    """Resposta parcial descartada: fica só o registro de que ela não foi concluída.

    Sessão própria: a sessão do stream pode estar em uso por uma thread interrompida.
    """
    with Session(session.get_bind()) as own:
        own.add(Message(conversation_id=conversation_id, role="assistant", content="", status="error"))
        own.commit()


def _save_answer(
    session: Session, conversation_id: int, content: str, cited: list[tuple[int, RetrievedChunk]], uncited: bool
) -> Message:
    message = Message(conversation_id=conversation_id, role="assistant", content=content, uncited=uncited)
    session.add(message)
    session.flush()
    session.add_all(
        Citation(message_id=message.id, chunk_id=s.chunk_id, document_id=s.document_id, marker=marker,
                 filename=s.filename, page_number=s.page_number, excerpt=s.content)
        for marker, s in cited
    )
    session.commit()
    return message

