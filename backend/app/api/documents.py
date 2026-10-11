from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import DocumentQuestionItem, DocumentResponse, DocumentStatusResponse
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse)
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await document_service.upload_document(db, current_user.id, file, background_tasks)


@router.get("", response_model=list[DocumentResponse])
def list_docs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return document_service.list_documents(db, current_user.id)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_doc(document_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return document_service.get_document(db, current_user.id, document_id)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def doc_status(document_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return document_service.get_document_status(db, current_user.id, document_id)


@router.get("/{document_id}/questions", response_model=list[DocumentQuestionItem])
def doc_questions(document_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return document_service.get_document_questions(db, current_user.id, document_id)


@router.get("/{document_id}/suggested-questions", response_model=list[str])
def suggested(document_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return document_service.suggested_questions(db, current_user.id, document_id)


@router.delete("/{document_id}")
def delete_doc(document_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return document_service.soft_delete_document(db, current_user.id, document_id)
