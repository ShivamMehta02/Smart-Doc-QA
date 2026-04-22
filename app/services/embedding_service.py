import numpy as np
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    """Load embedding model once, cache for lifetime of process."""
    logger.info("loading_embedding_model", model=settings.EMBEDDING_MODEL)
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Embed a list of texts → normalized float32 numpy array.
    Shape: (len(texts), EMBEDDING_DIMENSION)
    """
    model = _load_model()
    vectors = model.encode(texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True)
    vectors = vectors.astype(np.float32)
    return vectors


def embed_query(query: str) -> np.ndarray:
    """Embed a single query → shape (1, EMBEDDING_DIMENSION)"""
    model = _load_model()
    vector = model.encode([query], convert_to_numpy=True).astype(np.float32)
    return vector
