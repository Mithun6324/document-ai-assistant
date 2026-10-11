from functools import lru_cache
from typing import Optional

import numpy as np

from app.utils.logging import get_logger

logger = get_logger(__name__)

_MODEL = None


def get_embedding_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model all-MiniLM-L6-v2")
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model ready (384-dim)")
    return _MODEL


class EmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = get_embedding_model()
        vectors = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return [v.tolist() for v in np.asarray(vectors)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
