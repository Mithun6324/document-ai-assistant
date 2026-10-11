from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    page_count: int
    chunk_count: int
    status: str
    progress_stage: Optional[str] = None
    progress_percent: int
    processing_error: Optional[str] = None
    question_count: int = 0
    created_at: datetime
    updated_at: datetime
    duplicate: bool = False

    model_config = {"from_attributes": True}


class DocumentStatusResponse(BaseModel):
    id: UUID
    status: str
    progress_stage: Optional[str] = None
    progress_percent: int
    processing_error: Optional[str] = None
    chunk_count: int
    page_count: int


class DocumentQuestionItem(BaseModel):
    message_id: UUID
    conversation_id: UUID
    question: str
    answer_preview: Optional[str] = None
    asked_at: datetime


# ── Chat ───────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[UUID] = None
    document_ids: Optional[list[UUID]] = None


class SourceItem(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    similarity_score: float
    text_preview: str


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    answer: str
    sources: list[SourceItem] = []
    title: str


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    sources: Optional[list[Any]] = None
    retrieved_chunks: Optional[list[Any]] = None
    feedback: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    scope: str
    document_ids: list[Any] = []
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    id: UUID
    title: str
    scope: str
    document_ids: list[Any] = []
    messages: list[MessageResponse] = []
    created_at: datetime
    updated_at: datetime


class FeedbackRequest(BaseModel):
    rating: str = Field(pattern="^(up|down)$")
    comment: Optional[str] = None


class DashboardStats(BaseModel):
    total_documents: int
    ready_documents: int
    processing_documents: int
    total_queries: int
    recent_documents: list[DocumentResponse] = []
    recent_conversations: list[ConversationSummary] = []


class HealthResponse(BaseModel):
    status: str
    database: str
    chroma: str
    embedding_model: str
