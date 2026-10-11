from functools import lru_cache

from app.config import get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.deepseek_service import DeepSeekService
from app.services.llm.gemini_service import GeminiService
from app.utils.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = (settings.llm_provider or "gemini").lower()
    if provider == "deepseek":
        logger.info("Using DeepSeek LLM provider")
        return DeepSeekService()
    logger.info("Using Gemini LLM provider (%s)", settings.gemini_model)
    return GeminiService()
