from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


SYSTEM_PROMPT = """You are a Document AI Assistant.

Rules:
- Answer only from the provided context.
- Do not hallucinate or use outside knowledge.
- If the answer is unavailable in the context, reply exactly: The answer was not found in the uploaded document.
- Use citations whenever possible (page number, chunk id, document name).
- Be concise and professional.
"""


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, context: str, question: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def stream(self, context: str, question: str) -> AsyncIterator[str]:
        raise NotImplementedError
