import hashlib
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}


def validate_upload(file: UploadFile, content: bytes) -> str:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are supported",
        )

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        # Allow octet-stream for some browsers; still enforce extension
        if file.content_type != "application/octet-stream":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported content type: {file.content_type}",
            )

    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file is not allowed")

    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of {settings.max_file_size_mb} MB",
        )

    return ext.lstrip(".")


def file_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


PAGE_NUMBER_RE = re.compile(r"(?im)^(?:page\s*)?\d+(?:\s*(?:of|/)\s*\d+)?\s*$")
HEADER_FOOTER_RE = re.compile(r"(?im)^(?:confidential|internal use only|all rights reserved).*$")
MULTI_BLANK_RE = re.compile(r"\n{3,}")
MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
NOISE_SYMBOLS_RE = re.compile(r"[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\/\'\"\@\#\$\%\&\+\=\*\n]")
