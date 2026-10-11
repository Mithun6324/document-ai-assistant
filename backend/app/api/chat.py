import json
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import SessionLocal, get_db
from app.models import User
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
    DashboardStats,
    FeedbackRequest,
    MessageResponse,
)
from app.services import chat_service

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await chat_service.chat(db, current_user.id, payload)


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest, current_user: User = Depends(get_current_user)):
    user_id = current_user.id

    async def event_generator():
        db = SessionLocal()
        try:
            async for event in chat_service.chat_stream_events(db, user_id, payload):
                yield f"data: {event}\n\n"
            yield "data: {\"type\": \"end\"}\n\n"
        finally:
            db.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/chat/history", response_model=list[ConversationSummary])
def history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return chat_service.list_conversations(db, current_user.id)


@router.get("/chat/history/{conversation_id}", response_model=ConversationDetail)
def history_detail(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return chat_service.get_conversation(db, current_user.id, conversation_id)


@router.get("/chat/history/{conversation_id}/export")
def export_chat(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    md = chat_service.export_conversation_markdown(db, current_user.id, conversation_id)
    return PlainTextResponse(md, media_type="text/markdown")


@router.patch("/chat/messages/{message_id}/feedback", response_model=MessageResponse)
def feedback(
    message_id: UUID,
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return chat_service.set_feedback(db, current_user.id, message_id, payload)


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return chat_service.dashboard_stats(db, current_user.id)
