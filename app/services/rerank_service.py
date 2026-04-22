from typing import List
from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from sentence_transformers import CrossEncoder
    _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    USE_CROSS_ENCODER = True
    logger.info("cross_encoder_loaded")
except Exception:
    USE_CROSS_ENCODER = False
    logger.warning("cross_encoder_unavailable", fallback="cosine_score_sort")


def cross_encoder_rerank(question: str, candidates: List[dict], top_n: int = 5) -> List[dict]:
    """
    Re-rank retrieved chunks using cross-encoder.
    Falls back to cosine score sort if cross-encoder unavailable.
    
    candidates: [{"chunk_id": str, "text": str, "score": float, "page": int}]
    """
    if not candidates:
        return []

    if USE_CROSS_ENCODER:
        pairs = [(question, c["text"]) for c in candidates]
        scores = _cross_encoder.predict(pairs)
        for i, c in enumerate(candidates):
            c["rerank_score"] = float(scores[i])
        ranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
    else:
        # Fallback: sort by original cosine score
        ranked = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)

    return ranked[:top_n]
