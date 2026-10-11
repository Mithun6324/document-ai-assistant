from functools import lru_cache
from typing import Any, Optional

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ChromaService:
    def __init__(self):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection ready: %s", settings.chroma_collection)

    def add_chunks(
        self,
        chunk_ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        # Chroma metadata values must be str/int/float/bool
        clean_meta = []
        for m in metadatas:
            clean_meta.append(
                {
                    k: ("" if v is None else v)
                    for k, v in m.items()
                    if isinstance(v, (str, int, float, bool)) or v is None
                }
            )
        self.collection.upsert(
            ids=chunk_ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=clean_meta,
        )
        logger.info("Upserted %s chunks into ChromaDB", len(chunk_ids))

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        user_id: str,
        document_ids: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        where: dict[str, Any]
        if document_ids:
            where = {
                "$and": [
                    {"user_id": user_id},
                    {"document_id": {"$in": document_ids}},
                ]
            }
        else:
            where = {"user_id": user_id}

        try:
            result = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error("Chroma query failed: %s", exc)
            # Fallback without filter if collection empty
            return []

        items: list[dict[str, Any]] = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]

        for i, chunk_id in enumerate(ids):
            distance = dists[i] if i < len(dists) else 1.0
            # Cosine distance → similarity
            similarity = 1.0 - float(distance)
            meta = metas[i] if i < len(metas) else {}
            items.append(
                {
                    "chunk_id": chunk_id,
                    "text": docs[i] if i < len(docs) else "",
                    "similarity_score": round(similarity, 4),
                    "metadata": meta,
                }
            )

        logger.info("Chroma query returned %s results (user=%s)", len(items), user_id)
        return items

    def delete_by_document(self, document_id: str, user_id: str) -> None:
        try:
            self.collection.delete(where={"$and": [{"document_id": document_id}, {"user_id": user_id}]})
            logger.info("Deleted Chroma chunks for document %s", document_id)
        except Exception as exc:
            logger.warning("Chroma delete failed for %s: %s", document_id, exc)

    def health(self) -> str:
        try:
            _ = self.collection.count()
            return "ok"
        except Exception as exc:
            return f"error: {exc}"


@lru_cache
def get_chroma_service() -> ChromaService:
    return ChromaService()
