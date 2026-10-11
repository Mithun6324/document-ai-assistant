import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AuditLog, Conversation, Document, Message
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
    DashboardStats,
    DocumentResponse,
    FeedbackRequest,
    MessageResponse,
    SourceItem,
)
from app.services.document_service import list_documents
from app.services.llm import get_llm_provider
from app.services.retrieval_service import build_context_block, format_sources, retrieve
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _title_from_question(question: str) -> str:
    q = " ".join(question.strip().split())
    return q[:60] + ("…" if len(q) > 60 else "")


def _get_or_create_conversation(
    db: Session,
    user_id: UUID,
    conversation_id: Optional[UUID],
    document_ids: Optional[list[UUID]],
    question: str,
) -> Conversation:
    if conversation_id:
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        return conv

    scope = "selected" if document_ids else "all"
    conv = Conversation(
        user_id=user_id,
        title=_title_from_question(question),
        scope=scope,
        document_ids=[str(d) for d in (document_ids or [])],
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _validate_document_ids(db: Session, user_id: UUID, document_ids: Optional[list[UUID]]) -> Optional[list[str]]:
    if not document_ids:
        return None
    docs = (
        db.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.id.in_(document_ids),
            Document.deleted_at.is_(None),
            Document.status == "ready",
        )
        .all()
    )
    if len(docs) != len(set(document_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more documents are invalid, deleted, or not ready",
        )
    return [str(d.id) for d in docs]


async def chat(db: Session, user_id: UUID, payload: ChatRequest) -> ChatResponse:
    doc_ids = _validate_document_ids(db, user_id, payload.document_ids)
    conv = _get_or_create_conversation(db, user_id, payload.conversation_id, payload.document_ids, payload.question)

    chunks, early = retrieve(db, str(user_id), payload.question, doc_ids)

    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=payload.question,
        retrieved_chunks=[{**c, "text": c["text"][:500]} for c in chunks] if chunks else [],
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    if early:
        answer = early
        sources: list[dict] = []
    else:
        context = build_context_block(chunks)
        try:
            answer = await get_llm_provider().generate(context, payload.question)
        except Exception as exc:
            logger.error("LLM error: %s", exc)
            answer = "Sorry, the AI service is temporarily unavailable. Please try again."
        sources = format_sources(chunks)

    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=answer,
        sources=sources,
        retrieved_chunks=[{**c, "text": c["text"][:500]} for c in chunks] if chunks else [],
    )
    db.add(assistant_msg)
    conv.updated_at = datetime.now(timezone.utc)
    if conv.title == "New conversation":
        conv.title = _title_from_question(payload.question)
    db.add(AuditLog(user_id=user_id, action="chat", metadata_json={"conversation_id": str(conv.id)}))
    db.commit()
    db.refresh(assistant_msg)

    return ChatResponse(
        conversation_id=conv.id,
        message_id=assistant_msg.id,
        answer=answer,
        sources=[SourceItem(**s) for s in sources],
        title=conv.title,
    )


async def chat_stream_events(
    db: Session,
    user_id: UUID,
    payload: ChatRequest,
) -> AsyncIterator[str]:
    """Yields SSE data lines (JSON strings)."""
    doc_ids = _validate_document_ids(db, user_id, payload.document_ids)
    conv = _get_or_create_conversation(db, user_id, payload.conversation_id, payload.document_ids, payload.question)

    chunks, early = retrieve(db, str(user_id), payload.question, doc_ids)

    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=payload.question,
        retrieved_chunks=[{**c, "text": c["text"][:500]} for c in chunks] if chunks else [],
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    yield json.dumps({"type": "meta", "conversation_id": str(conv.id), "title": conv.title})

    answer_parts: list[str] = []
    sources: list[dict] = []

    if early:
        answer_parts.append(early)
        yield json.dumps({"type": "token", "content": early})
    else:
        sources = format_sources(chunks)
        yield json.dumps({"type": "sources", "sources": sources})
        context = build_context_block(chunks)
        try:
            async for token in get_llm_provider().stream(context, payload.question):
                answer_parts.append(token)
                yield json.dumps({"type": "token", "content": token})
        except Exception as exc:
            logger.error("LLM stream error: %s", exc)
            msg = "Sorry, the AI service is temporarily unavailable. Please try again."
            answer_parts.append(msg)
            yield json.dumps({"type": "token", "content": msg})

    answer = "".join(answer_parts)
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=answer,
        sources=sources,
        retrieved_chunks=[{**c, "text": c["text"][:500]} for c in chunks] if chunks else [],
    )
    db.add(assistant_msg)
    conv.updated_at = datetime.now(timezone.utc)
    if conv.title == "New conversation":
        conv.title = _title_from_question(payload.question)
    db.commit()
    db.refresh(assistant_msg)

    yield json.dumps(
        {
            "type": "done",
            "message_id": str(assistant_msg.id),
            "conversation_id": str(conv.id),
            "sources": sources,
            "title": conv.title,
        }
    )


def list_conversations(db: Session, user_id: UUID) -> list[ConversationSummary]:
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    result = []
    for c in convs:
        result.append(
            ConversationSummary(
                id=c.id,
                title=c.title,
                scope=c.scope,
                document_ids=c.document_ids or [],
                message_count=len(c.messages),
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return result


def get_conversation(db: Session, user_id: UUID, conversation_id: UUID) -> ConversationDetail:
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        scope=conv.scope,
        document_ids=conv.document_ids or [],
        messages=[MessageResponse.model_validate(m) for m in conv.messages],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


def export_conversation_markdown(db: Session, user_id: UUID, conversation_id: UUID) -> str:
    detail = get_conversation(db, user_id, conversation_id)
    lines = [f"# {detail.title}", "", f"_Exported conversation_", ""]
    for m in detail.messages:
        role = "User" if m.role == "user" else "Assistant"
        lines.append(f"## {role}")
        lines.append("")
        lines.append(m.content)
        lines.append("")
        if m.sources:
            lines.append("**Sources:**")
            for s in m.sources:
                if isinstance(s, dict):
                    lines.append(
                        f"- {s.get('document_name')} | Page {s.get('page_number')} | "
                        f"Chunk `{s.get('chunk_id')}` | score={s.get('similarity_score')}"
                    )
            lines.append("")
    return "\n".join(lines)


def set_feedback(db: Session, user_id: UUID, message_id: UUID, payload: FeedbackRequest) -> MessageResponse:
    msg = (
        db.query(Message)
        .join(Conversation)
        .filter(Message.id == message_id, Conversation.user_id == user_id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if msg.role != "assistant":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Feedback only for assistant messages")
    msg.feedback = payload.rating
    msg.feedback_comment = payload.comment
    db.commit()
    db.refresh(msg)
    return MessageResponse.model_validate(msg)


def dashboard_stats(db: Session, user_id: UUID) -> DashboardStats:
    docs = list_documents(db, user_id)
    total_docs = len(docs)
    ready = sum(1 for d in docs if d.status == "ready")
    processing = sum(1 for d in docs if d.status in ("pending", "processing"))
    total_queries = (
        db.query(func.count(Message.id))
        .join(Conversation)
        .filter(Conversation.user_id == user_id, Message.role == "user")
        .scalar()
        or 0
    )
    recent_convs = list_conversations(db, user_id)[:5]
    return DashboardStats(
        total_documents=total_docs,
        ready_documents=ready,
        processing_documents=processing,
        total_queries=int(total_queries),
        recent_documents=docs[:5],
        recent_conversations=recent_convs,
    )
