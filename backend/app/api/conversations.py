import json
from collections.abc import AsyncIterator
from contextlib import aclosing
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, sessionmaker

from app.chat.answer import AnswerConfig, Event, answer_question
from app.chat.conversations import (
    ConversationState,
    close_open,
    conversation_state,
    create_conversation,
    delete_conversation,
    get_detail,
    list_conversations,
)
from app.core.config import Settings, get_settings
from app.core.deps import get_embedder_loader, get_llm, get_session, get_session_factory
from app.embeddings.model import EmbedderLoader
from app.llm.provider import LLMProvider

router = APIRouter(prefix="/conversations", tags=["conversas"])

SessionDep = Annotated[Session, Depends(get_session)]


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    created_at: datetime
    closed_at: datetime | None


class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    marker: int
    document_id: int
    chunk_id: int | None
    filename: str
    page_number: int
    excerpt: str
    document_removed: bool


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    status: str
    uncited: bool
    created_at: datetime
    citations: list[CitationOut]


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


@router.post("", response_model=ConversationOut, status_code=201)
def create(session: SessionDep):
    return create_conversation(session)


@router.post("/close-open", status_code=204)
def close_all_open(session: SessionDep):
    close_open(session)


@router.get("", response_model=list[ConversationOut])
def list_all(session: SessionDep):
    return list_conversations(session)


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_one(conversation_id: int, session: SessionDep):
    detail = get_detail(session, conversation_id)
    if detail is None:
        raise HTTPException(404, "conversa não encontrada")
    base = ConversationOut.model_validate(detail.conversation)
    return ConversationDetailOut(**base.model_dump(), messages=[MessageOut.model_validate(m) for m in detail.messages])


@router.delete("/{conversation_id}", status_code=204)
def delete(conversation_id: int, session: SessionDep):
    if not delete_conversation(session, conversation_id):
        raise HTTPException(404, "conversa não encontrada")


class QuestionIn(BaseModel):
    # Limite para a pergunta não estourar o orçamento de tokens (seção 6.7).
    content: str = Field(min_length=1, max_length=2000)


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    question: QuestionIn,
    request: Request,
    session: SessionDep,
    sessions: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    settings: Annotated[Settings, Depends(get_settings)],
    loader: Annotated[EmbedderLoader, Depends(get_embedder_loader)],
    llm: Annotated[LLMProvider, Depends(get_llm)],
):
    """Pergunta por POST, resposta por SSE (seção 6.5)."""
    state = await run_in_threadpool(conversation_state, session, conversation_id)
    if state is ConversationState.NOT_FOUND:
        raise HTTPException(404, "conversa não encontrada")
    if state is ConversationState.CLOSED:  # o front trata esse 409 especificamente (seção 7)
        raise HTTPException(409, "esta conversa foi encerrada")
    if loader.embedder is None:
        raise HTTPException(503, "o modelo de busca ainda está carregando; tente de novo em instantes")
    config = AnswerConfig(settings.llm_answer_model, settings.llm_rewrite_model, settings.top_k,
                          settings.min_similarity, settings.history_turns)

    async def stream() -> AsyncIterator[str]:
        with sessions() as stream_session:
            events = answer_question(stream_session, llm, loader.embedder, config, conversation_id, question.content)
            async with aclosing(events):
                async for event in events:
                    if await request.is_disconnected():
                        break  # aclosing encerra a geração e grava a resposta como `error` (seção 6.6)
                    yield _sse(event)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _sse(event: Event) -> str:
    return f"event: {event.name}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"
