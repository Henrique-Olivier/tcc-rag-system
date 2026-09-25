"""Ciclo de vida e consulta das conversas (plano, seções 4 e 7)."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.orm import Session

from app.db.models import Citation, Conversation, Document, Message


class ConversationState(Enum):
    OPEN = "open"
    CLOSED = "closed"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class CitationView:
    marker: int
    document_id: int
    chunk_id: int
    filename: str
    page_number: int
    excerpt: str
    document_removed: bool  # aviso de remoção no front (CA16)


@dataclass(frozen=True)
class MessageView:
    id: int
    role: str
    content: str
    status: str
    created_at: datetime
    citations: list[CitationView]


@dataclass(frozen=True)
class ConversationDetail:
    conversation: Conversation
    messages: list[MessageView]


def close_open(session: Session) -> None:
    """Fecha todas as conversas abertas: "fechar o sistema" do CA13."""
    session.execute(update(Conversation).where(Conversation.closed_at.is_(None)).values(closed_at=func.now()))
    session.commit()


def create_conversation(session: Session) -> Conversation:
    """Só uma conversa fica aberta por vez (seção 7)."""
    session.execute(update(Conversation).where(Conversation.closed_at.is_(None)).values(closed_at=func.now()))
    conversation = Conversation()
    session.add(conversation)
    session.commit()
    return conversation


def conversation_state(session: Session, conversation_id: int) -> ConversationState:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        return ConversationState.NOT_FOUND
    return ConversationState.OPEN if conversation.closed_at is None else ConversationState.CLOSED


def list_conversations(session: Session) -> list[Conversation]:
    """Conversas sem nenhuma mensagem não aparecem (seção 7)."""
    has_messages = exists().where(Message.conversation_id == Conversation.id)
    return list(session.scalars(select(Conversation).where(has_messages).order_by(Conversation.created_at.desc(), Conversation.id.desc())))


def get_detail(session: Session, conversation_id: int) -> ConversationDetail | None:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        return None
    messages = session.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)).all()
    citations: dict[int, list[CitationView]] = {}
    rows = session.execute(
        select(Citation, Document.deleted_at)
        .join(Document, Document.id == Citation.document_id)
        .where(Citation.message_id.in_([m.id for m in messages]))
        .order_by(Citation.marker)
    )
    for c, deleted_at in rows:
        citations.setdefault(c.message_id, []).append(
            CitationView(c.marker, c.document_id, c.chunk_id, c.filename, c.page_number, c.excerpt, deleted_at is not None)
        )
    views = [MessageView(m.id, m.role, m.content, m.status, m.created_at, citations.get(m.id, [])) for m in messages]
    return ConversationDetail(conversation, views)


def delete_conversation(session: Session, conversation_id: int) -> bool:
    """Exclusão definitiva; mensagens e citações caem em cascata no banco (CA15)."""
    deleted = session.execute(delete(Conversation).where(Conversation.id == conversation_id)).rowcount
    session.commit()
    return deleted > 0
