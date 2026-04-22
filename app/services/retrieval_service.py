from typing import List, Tuple
from app.services.embedding_service import embed_query
from app.vectorstore.faiss_store import get_faiss_store
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def retrieve_chunks(doc_id: str, question: str, top_k: int = None) -> List[Tuple[str, float]]:
    """
    Step 1: Embed the query
    Step 2: Search FAISS for nearest neighbors
    Returns [(chunk_id, cosine_score)]
    """
    k = top_k or settings.MAX_RETRIEVAL_K
    query_vec = embed_query(question)
    store = get_faiss_store(doc_id)
    results = store.search(query_vec, top_k=k)
    logger.info("retrieval_done", doc_id=doc_id, results=len(results))
    return results


def rerank_results(question: str, candidates: List[dict]) -> List[dict]:
    """
    Re-rank candidates using cross-encoder or cosine similarity refinement.
    
    Strategy: cosine refinement using query-chunk similarity (lightweight).
    For production: swap in cross-encoder/ms-marco-MiniLM-L-6-v2.
    
    Why not always use cross-encoder?
    → Cross-encoder latency: ~40ms per doc. For 10 docs: 400ms.
    → Cosine refinement: ~5ms for all. Sufficient for most use cases.
    → Add cross-encoder if precision requirements are very high.
    """
    from app.services.rerank_service import cross_encoder_rerank
    return cross_encoder_rerank(question, candidates, top_n=settings.RERANK_TOP_N)
