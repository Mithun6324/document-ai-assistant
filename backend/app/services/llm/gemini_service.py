# Gemini SDK (legacy package still widely used for streaming)
import google.generativeai as genai_legacy

from app.config import get_settings
from app.services.llm.base import SYSTEM_PROMPT, LLMProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class GeminiService(LLMProvider):
    def __init__(self):
        if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
            logger.warning("GEMINI_API_KEY not configured")
        genai_legacy.configure(api_key=settings.gemini_api_key)
        self.model = genai_legacy.GenerativeModel(
            model_name=settings.gemini_model,
            system_instruction=SYSTEM_PROMPT,
        )

    def _prompt(self, context: str, question: str) -> str:
        return f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"

    async def generate(self, context: str, question: str) -> str:
        try:
            response = self.model.generate_content(self._prompt(context, question))
            text = (response.text or "").strip()
            logger.info("Gemini response length=%s", len(text))
            return text or "The answer was not found in the uploaded document."
        except Exception as exc:
            logger.error("Gemini generate failed: %s", exc)
            raise

    async def stream(self, context: str, question: str):
        try:
            response = self.model.generate_content(self._prompt(context, question), stream=True)
            for chunk in response:
                try:
                    part = chunk.text
                except Exception:
                    part = None
                if part:
                    yield part
        except Exception as exc:
            logger.error("Gemini stream failed: %s", exc)
            raise
