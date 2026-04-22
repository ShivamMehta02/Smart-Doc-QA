import threading
import os
import numpy as np
import faiss
from typing import List, Tuple, Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class FAISSStore:
    """
    Thread-safe FAISS singleton.
    
    Why thread-safe?
    FAISS indices are NOT thread-safe by default. Without a lock,
    concurrent writes corrupt the index silently. This wrapper
    uses a RW-style lock: many readers, one writer.
    """

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self.dimension = settings.EMBEDDING_DIMENSION
        self._index: Optional[faiss.Index] = None
        self._chunk_ids: List[str] = []
        self._lock = threading.RLock()
        self._index_path = os.path.join(settings.FAISS_INDEX_PATH, f"{doc_id}.index")
        self._meta_path = os.path.join(settings.FAISS_INDEX_PATH, f"{doc_id}.meta.npy")

    def _ensure_index(self):
        if self._index is None:
            if os.path.exists(self._index_path):
                self._index = faiss.read_index(self._index_path)
                self._chunk_ids = list(np.load(self._meta_path, allow_pickle=True))
            else:
                # IVF flat for large corpora, flat for small
                self._index = faiss.IndexFlatIP(self.dimension)  # Inner product (for normalized vectors = cosine)

    def add_vectors(self, vectors: np.ndarray, chunk_ids: List[str]) -> None:
        """Add embeddings to FAISS index. vectors must be L2-normalized."""
        with self._lock:
            self._ensure_index()
            faiss.normalize_L2(vectors)
            self._index.add(vectors)
            self._chunk_ids.extend(chunk_ids)
            self._persist()

    def search(self, query_vector: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        """Returns [(chunk_id, cosine_score)] sorted by score desc."""
        with self._lock:
            self._ensure_index()
            if self._index.ntotal == 0:
                return []
            faiss.normalize_L2(query_vector)
            k = min(top_k, self._index.ntotal)
            scores, indices = self._index.search(query_vector, k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self._chunk_ids):
                    results.append((self._chunk_ids[idx], float(score)))
            return results

    def _persist(self):
        os.makedirs(settings.FAISS_INDEX_PATH, exist_ok=True)
        faiss.write_index(self._index, self._index_path)
        np.save(self._meta_path, np.array(self._chunk_ids, dtype=object))

    def delete(self):
        """Remove index files from disk."""
        with self._lock:
            for path in [self._index_path, self._meta_path]:
                if os.path.exists(path):
                    os.remove(path)
            self._index = None
            self._chunk_ids = []


# ── Store Registry — one FAISSStore per document ──────────────────────────────
_store_registry: dict[str, FAISSStore] = {}
_registry_lock = threading.Lock()


def get_faiss_store(doc_id: str) -> FAISSStore:
    """Get or create a FAISSStore for a document."""
    with _registry_lock:
        if doc_id not in _store_registry:
            _store_registry[doc_id] = FAISSStore(doc_id)
        return _store_registry[doc_id]


def remove_faiss_store(doc_id: str):
    with _registry_lock:
        store = _store_registry.pop(doc_id, None)
        if store:
            store.delete()
