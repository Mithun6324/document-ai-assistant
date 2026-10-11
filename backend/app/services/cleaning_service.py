import re

from app.utils.file_validation import (
    HEADER_FOOTER_RE,
    MULTI_BLANK_RE,
    MULTI_SPACE_RE,
    NOISE_SYMBOLS_RE,
    PAGE_NUMBER_RE,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


def clean_text(text: str) -> str:
    if not text:
        return ""

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
        if PAGE_NUMBER_RE.match(stripped):
            continue
        if HEADER_FOOTER_RE.match(stripped):
            continue
        cleaned_lines.append(stripped)

    result = "\n".join(cleaned_lines)
    result = MULTI_BLANK_RE.sub("\n\n", result)
    result = MULTI_SPACE_RE.sub(" ", result)
    result = NOISE_SYMBOLS_RE.sub("", result)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()

    logger.debug("Cleaned text length: %s", len(result))
    return result
