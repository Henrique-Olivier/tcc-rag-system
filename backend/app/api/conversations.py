from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.chat.conversations import (
    close_open,
    create_conversation,
    delete_conversation,
    get_detail,
    list_conversations,
)
from app.core.deps import get_session

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
    chunk_id: int
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
