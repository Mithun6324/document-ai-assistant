from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import AuditLog, User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.utils.logging import get_logger
from app.utils.security import create_access_token, hash_password, verify_password

logger = get_logger(__name__)


def register_user(db: Session, payload: RegisterRequest) -> UserResponse:
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.add(AuditLog(user_id=None, action="user_register", metadata_json={"email": payload.email.lower()}))
    db.commit()
    db.refresh(user)
    logger.info("User registered: %s", user.email)
    return UserResponse.model_validate(user)


def login_user(db: Session, payload: LoginRequest) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(str(user.id), extra={"email": user.email})
    db.add(AuditLog(user_id=user.id, action="user_login", metadata_json={"email": user.email}))
    db.commit()
    logger.info("User logged in: %s", user.email)
    return TokenResponse(access_token=token)


def get_user_by_id(db: Session, user_id: UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
