from typing import List, Tuple
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

NOT_IN_DOCUMENT_SIGNAL = "NOT_IN_DOCUMENT"
FALLBACK_ANSWER = "The answer to your question was not found in the provided document."


def validate_and_score(answer: str, context_chunks: List[dict], top_score: float) -> Tuple[str, float, bool]:
    """
    Hallucination check + confidence scoring.
    
    Returns: (final_answer, confidence_score, is_fallback)
    
    Strategy:
    1. Check if LLM returned the NOT_IN_DOCUMENT signal
    2. Verify answer has word overlap with context (basic hallucination check)
    3. Compute confidence from retrieval score
    """
    # Step 1: LLM explicitly says answer not in document
    if NOT_IN_DOCUMENT_SIGNAL in answer:
        logger.info("validation_fallback", reason="llm_signal")
        return FALLBACK_ANSWER, 0.0, True

    # Step 2: Basic hallucination check — does the answer share words with context?
    if settings.HALLUCINATION_CHECK and context_chunks:
        context_text = " ".join(c["text"] for c in context_chunks).lower()
        answer_words = set(answer.lower().split())
        context_words = set(context_text.split())
        overlap = len(answer_words & context_words)
        overlap_ratio = overlap / max(len(answer_words), 1)

        if overlap_ratio < 0.15:  # Less than 15% word overlap → likely hallucination
            logger.warning("hallucination_detected", overlap_ratio=overlap_ratio)
            return FALLBACK_ANSWER, 0.0, True

    # Step 3: Confidence from top retrieval score (cosine similarity 0–1)
    confidence = min(round(float(top_score), 3), 1.0)

    # Below threshold → low confidence fallback
    if confidence < settings.CONFIDENCE_THRESHOLD:
        logger.info("validation_low_confidence", confidence=confidence)
        return FALLBACK_ANSWER, confidence, True

    return answer, confidence, False
