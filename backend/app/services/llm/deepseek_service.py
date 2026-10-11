from typing import AsyncIterator

import httpx

from app.config import get_settings
from app.services.llm.base import SYSTEM_PROMPT, LLMProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class DeepSeekService(LLMProvider):
    """Optional fallback provider (not used unless LLM_PROVIDER=deepseek)."""

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url.rstrip("/")

    def _messages(self, context: str, question: str) -> list[dict]:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"},
        ]

    async def generate(self, context: str, question: str) -> str:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not configured")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "deepseek-chat",
                    "messages": self._messages(context, question),
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    async def stream(self, context: str, question: str) -> AsyncIterator[str]:
        # Simple non-stream fallback yielding full answer
        text = await self.generate(context, question)
        yield text
