from functools import lru_cache
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Chunk, Document
from app.services.chroma_service import get_chroma_service
from app.services.embedding_service import get_embedding_service
from app.utils.file_validation import estimate_tokens
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

NOT_RELATED_MSG = "This question is not related to the uploaded document."


@lru_cache
def get_reranker():
    """Load CrossEncoder once and reuse across requests (same accuracy, much faster)."""
    from sentence_transformers import CrossEncoder

    logger.info("Loading CrossEncoder re-ranker (one-time)")
    model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    logger.info("CrossEncoder re-ranker ready")
    return model


def _keyword_search(
    db: Session,
    user_id: str,
    query: str,
    document_ids: Optional[list[str]],
    limit: int,
) -> list[dict[str, Any]]:
    q = (
        db.query(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .filter(Document.user_id == user_id, Document.deleted_at.is_(None), Document.status == "ready")
    )
    if document_ids:
        q = q.filter(Chunk.document_id.in_(document_ids))

    terms = [t.strip() for t in query.lower().split() if len(t.strip()) > 2][:8]
    if not terms:
        return []

    # Simple ILIKE scoring
    rows = q.limit(200).all()
    scored = []
    for chunk, doc in rows:
        text_l = chunk.text.lower()
        hits = sum(1 for t in terms if t in text_l)
        if hits == 0:
            continue
        score = hits / len(terms)
        scored.append(
            {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "similarity_score": round(min(0.95, 0.4 + score * 0.5), 4),
                "metadata": {
                    "document_id": str(doc.id),
                    "document_name": doc.original_filename,
                    "page_number": chunk.page_number or 0,
                    "section_name": chunk.section_name or "",
                    "chunk_type": chunk.chunk_type,
                    "user_id": str(user_id),
                },
                "_source": "keyword",
            }
        )
    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored[:limit]


def _rerank(query: str, candidates: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    if not candidates:
        return []
    try:
        model = get_reranker()
        pairs = [[query, c["text"]] for c in candidates]
        scores = model.predict(pairs)
        for i, c in enumerate(candidates):
            c["similarity_score"] = round(float(scores[i]), 4)
        mx = max(c["similarity_score"] for c in candidates) or 1.0
        mn = min(c["similarity_score"] for c in candidates)
        for c in candidates:
            if mx != mn:
                c["similarity_score"] = round((c["similarity_score"] - mn) / (mx - mn), 4)
            else:
                c["similarity_score"] = 0.7
        candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        logger.info("Re-ranked %s candidates", len(candidates))
        return candidates[:top_k]
    except Exception as exc:
        logger.warning("Re-ranker unavailable, using hybrid scores: %s", exc)
        candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        return candidates[:top_k]


def _merge_hybrid(vector_hits: list[dict], keyword_hits: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for item in vector_hits:
        cid = item["chunk_id"]
        by_id[cid] = {
            **item,
            "similarity_score": round(0.7 * item["similarity_score"], 4),
        }
    for item in keyword_hits:
        cid = item["chunk_id"]
        kw = 0.3 * item["similarity_score"]
        if cid in by_id:
            by_id[cid]["similarity_score"] = round(by_id[cid]["similarity_score"] + kw, 4)
        else:
            by_id[cid] = {**item, "similarity_score": round(kw + 0.3, 4)}
    merged = list(by_id.values())
    merged.sort(key=lambda x: x["similarity_score"], reverse=True)
    return merged


def _trim_context(chunks: list[dict], max_tokens: int) -> list[dict]:
    total = 0
    kept = []
    for c in chunks:
        est = estimate_tokens(c["text"])
        if total + est > max_tokens and kept:
            break
        kept.append(c)
        total += est
    if len(kept) < len(chunks):
        logger.info("Trimmed context from %s to %s chunks (token budget)", len(chunks), len(kept))
    return kept


def retrieve(
    db: Session,
    user_id: str,
    question: str,
    document_ids: Optional[list[str]] = None,
) -> tuple[list[dict[str, Any]], Optional[str]]:
    """
    Returns (chunks, early_message).
    If early_message is set, skip LLM.
    """
    # Ensure user has at least one ready doc in scope
    q = db.query(Document).filter(
        Document.user_id == user_id,
        Document.deleted_at.is_(None),
        Document.status == "ready",
    )
    if document_ids:
        q = q.filter(Document.id.in_(document_ids))
    if q.count() == 0:
        return [], "No ready documents available. Please upload a document first."

    embedding = get_embedding_service().embed_query(question)
    vector_hits = get_chroma_service().query(
        query_embedding=embedding,
        top_k=settings.retrieval_candidates,
        user_id=user_id,
        document_ids=document_ids,
    )
    keyword_hits = _keyword_search(
        db,
        user_id=user_id,
        query=question,
        document_ids=document_ids,
        limit=settings.retrieval_candidates,
    )

    merged = _merge_hybrid(vector_hits, keyword_hits)
    top = _rerank(question, merged[: settings.retrieval_candidates], settings.top_k)

    if not top or all(c["similarity_score"] < settings.similarity_threshold for c in top):
        logger.info("Similarity below threshold for question: %s", question[:80])
        return [], NOT_RELATED_MSG

    # Filter by threshold individually
    top = [c for c in top if c["similarity_score"] >= settings.similarity_threshold]
    if not top:
        return [], NOT_RELATED_MSG

    top = _trim_context(top, settings.max_context_tokens)

    logger.info(
        "Retrieval scores: %s",
        [(c["chunk_id"][:8], c["similarity_score"]) for c in top],
    )
    return top, None


def format_sources(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = []
    for c in chunks:
        meta = c.get("metadata") or {}
        preview = c["text"][:300] + ("..." if len(c["text"]) > 300 else "")
        sources.append(
            {
                "chunk_id": c["chunk_id"],
                "document_id": str(meta.get("document_id", "")),
                "document_name": meta.get("document_name", "unknown"),
                "page_number": meta.get("page_number") or None,
                "section_name": meta.get("section_name") or None,
                "similarity_score": c["similarity_score"],
                "text_preview": preview,
            }
        )
    return sources


def build_context_block(chunks: list[dict[str, Any]]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        meta = c.get("metadata") or {}
        parts.append(
            f"[Chunk {i} | id={c['chunk_id']} | doc={meta.get('document_name')} | "
            f"page={meta.get('page_number')} | section={meta.get('section_name')}]\n{c['text']}"
        )
    return "\n\n".join(parts)
