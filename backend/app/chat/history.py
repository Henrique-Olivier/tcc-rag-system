"""Preparação do histórico enviado à LLM (plano, seção 6.1)."""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.markers import MARKER_RE, expand_marker
from app.db.models import Citation, Document, Message


@dataclass(frozen=True)
class PastCitation:
    marker: int
    filename: str
    page_number: int
    document_removed: bool


@dataclass(frozen=True)
class PastMessage:
    role: str
    content: str
    status: str = "complete"
    citations: list[PastCitation] = field(default_factory=list)


@dataclass(frozen=True)
class HistoryTurn:
    question: str
    answer: str | None  # None: resposta omitida (erro ou documento removido)


def prepare_history(messages: list[PastMessage], turns: int) -> list[HistoryTurn]:
    """Últimas `turns` trocas, sem os marcadores originais: um [3] antigo apontava para outro trecho (CA07)."""
    grouped: list[tuple[str, PastMessage | None]] = []
    for message in messages:
        if message.role == "user":
            grouped.append((message.content, None))
        elif grouped and grouped[-1][1] is None:
            grouped[-1] = (grouped[-1][0], message)
    return [HistoryTurn(question, _prepared_answer(answer)) for question, answer in grouped[-turns:] if turns > 0]


def _prepared_answer(answer: PastMessage | None) -> str | None:
    if answer is None or answer.status != "complete":
        return None
    if any(c.document_removed for c in answer.citations):
        return None  # conteúdo de documento removido não volta a aparecer (CA05)
    references = {c.marker: f"{c.filename}, p. {c.page_number}" for c in answer.citations}
    upper = max(references, default=0)

    def replace(match) -> str:
        found = [references[n] for n in expand_marker(match.group(1), upper) if n in references]
        return f"({'; '.join(found)})" if found else ""

    return MARKER_RE.sub(replace, answer.content)


def load_messages(session: Session, conversation_id: int, before_message_id: int | None = None) -> list[PastMessage]:
    """Mensagens da conversa em ordem, com as citações e o estado do documento de cada uma."""
    query = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
    if before_message_id is not None:
        query = query.where(Message.id < before_message_id)
    messages = session.scalars(query).all()
    citations: dict[int, list[PastCitation]] = {}
    rows = session.execute(
        select(Citation, Document.deleted_at)
        .join(Document, Document.id == Citation.document_id)
        .where(Citation.message_id.in_([m.id for m in messages]))
        .order_by(Citation.marker)
    )
    for citation, deleted_at in rows:
        citations.setdefault(citation.message_id, []).append(
            PastCitation(citation.marker, citation.filename, citation.page_number, deleted_at is not None)
        )
    return [PastMessage(m.role, m.content, m.status, citations.get(m.id, [])) for m in messages]
