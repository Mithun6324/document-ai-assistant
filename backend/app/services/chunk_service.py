import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

SECTION_PATTERNS = [
    (r"(?i)^(skills|technical\s+skills|core\s+competencies)\b", "Skills"),
    (r"(?i)^(projects?|key\s+projects)\b", "Projects"),
    (r"(?i)^(experience|work\s+experience|professional\s+experience|employment)\b", "Experience"),
    (r"(?i)^(education|academic\s+background)\b", "Education"),
    (r"(?i)^(certifications?|licenses?)\b", "Certifications"),
    (r"(?i)^(summary|profile|objective|about)\b", "Summary"),
    (r"(?i)^(balance\s+sheet)\b", "Balance Sheet"),
    (r"(?i)^(income\s+statement|profit\s+and\s+loss|p\s*&\s*l)\b", "Income Statement"),
    (r"(?i)^(cash\s+flow)\b", "Cash Flow"),
    (r"(?i)^(notes?\s+to\s+(?:the\s+)?financials?)\b", "Financial Notes"),
    (r"(?i)^(introduction|overview|background)\b", "Introduction"),
    (r"(?i)^(conclusion|recommendations?)\b", "Conclusion"),
]

HEADER_LINE_RE = re.compile(r"^[A-Z][A-Za-z0-9 &\-/]{2,60}$")


@dataclass
class ChunkData:
    chunk_id: str
    text: str
    page_number: Optional[int]
    section_name: Optional[str]
    chunk_type: str
    created_at: str


def _detect_section(line: str) -> Optional[str]:
    stripped = line.strip()
    for pattern, name in SECTION_PATTERNS:
        if re.match(pattern, stripped):
            return name
    if HEADER_LINE_RE.match(stripped) and len(stripped.split()) <= 6:
        return stripped.title()
    return None


def _split_sentences(text: str, nlp) -> list[str]:
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def _split_with_overlap(text: str, max_size: int, overlap: int) -> list[str]:
    if len(text) <= max_size:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_size, len(text))
        if end < len(text):
            # Prefer break at sentence/space boundary
            window = text[start:end]
            break_at = max(window.rfind(". "), window.rfind("\n"), window.rfind(" "))
            if break_at > max_size // 3:
                end = start + break_at + 1
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return [p for p in parts if p]


def _ensure_size(text: str, nlp, chunk_type: str, page: Optional[int], section: Optional[str]) -> list[ChunkData]:
    max_size = settings.max_chunk_size
    overlap = settings.chunk_overlap
    now = datetime.now(timezone.utc).isoformat()

    if len(text) <= max_size:
        return [
            ChunkData(
                chunk_id=str(uuid.uuid4()),
                text=text,
                page_number=page,
                section_name=section,
                chunk_type=chunk_type,
                created_at=now,
            )
        ]

    # Sentence split first
    sentences = _split_sentences(text, nlp)
    chunks: list[ChunkData] = []
    buffer = ""
    for sent in sentences:
        if len(buffer) + len(sent) + 1 <= max_size:
            buffer = f"{buffer} {sent}".strip()
        else:
            if buffer:
                for part in _split_with_overlap(buffer, max_size, overlap):
                    chunks.append(
                        ChunkData(
                            chunk_id=str(uuid.uuid4()),
                            text=part,
                            page_number=page,
                            section_name=section,
                            chunk_type="sentence" if chunk_type != "section" else "section",
                            created_at=now,
                        )
                    )
            buffer = sent
    if buffer:
        for part in _split_with_overlap(buffer, max_size, overlap):
            chunks.append(
                ChunkData(
                    chunk_id=str(uuid.uuid4()),
                    text=part,
                    page_number=page,
                    section_name=section,
                    chunk_type="character" if len(part) > max_size else "sentence",
                    created_at=now,
                )
            )
    return chunks


def semantic_chunk(
    pages: list[dict],
    document_id: str,
    document_name: str,
) -> list[dict]:
    """
    pages: list of {"page_number": int, "text": str}
    Returns list of chunk dicts with full metadata.
    """
    try:
        import spacy

        nlp = spacy.load("en_core_web_sm")
    except Exception:
        logger.warning("spaCy model unavailable; using regex sentence split fallback")
        nlp = None

    all_chunks: list[ChunkData] = []
    current_section: Optional[str] = None

    for page in pages:
        page_num = page.get("page_number")
        text = (page.get("text") or "").strip()
        if not text:
            continue

        paragraphs = re.split(r"\n\s*\n", text)
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            lines = para.split("\n")
            first_line = lines[0].strip()
            detected = _detect_section(first_line)
            if detected:
                current_section = detected
                body = "\n".join(lines[1:]).strip() or para
                chunk_type = "section"
            else:
                body = para
                chunk_type = "paragraph"

            if nlp is not None:
                sized = _ensure_size(body, nlp, chunk_type, page_num, current_section)
            else:
                # Fallback without spaCy
                now = datetime.now(timezone.utc).isoformat()
                sized = []
                for part in _split_with_overlap(body, settings.max_chunk_size, settings.chunk_overlap):
                    sized.append(
                        ChunkData(
                            chunk_id=str(uuid.uuid4()),
                            text=part,
                            page_number=page_num,
                            section_name=current_section,
                            chunk_type=chunk_type,
                            created_at=now,
                        )
                    )
            all_chunks.extend(sized)

    result = []
    for c in all_chunks:
        result.append(
            {
                "chunk_id": c.chunk_id,
                "document_id": document_id,
                "document_name": document_name,
                "page_number": c.page_number,
                "section_name": c.section_name,
                "chunk_type": c.chunk_type,
                "created_at": c.created_at,
                "text": c.text,
            }
        )

    logger.info("Created %s semantic chunks for %s", len(result), document_name)
    return result
