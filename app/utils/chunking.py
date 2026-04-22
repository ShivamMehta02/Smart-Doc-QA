from typing import List, Dict, Any
from app.core.config import settings


def chunk_pages(pages: List[Dict[str, Any]], doc_id: str) -> List[Dict[str, Any]]:
    """
    Recursive character-level chunking with overlap.
    
    Why overlap?
    - Without overlap: answers that span chunk boundaries are missed
    - With overlap: context bleeds across chunk boundaries → better retrieval
    
    Chunk size 600 tokens / overlap 120 tokens is empirically validated
    for most document Q&A use cases.
    """
    chunk_size = settings.CHUNK_SIZE * 4   # approx chars
    overlap = settings.CHUNK_OVERLAP * 4   # approx chars

    chunks = []
    chunk_index = 0

    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"]

        # Recursive split on paragraph → sentence → word boundaries
        page_chunks = _recursive_split(text, chunk_size, overlap)

        for chunk_text in page_chunks:
            if chunk_text.strip():
                chunks.append({
                    "text": chunk_text.strip(),
                    "page": page_num,
                    "chunk_index": chunk_index,
                    "metadata": {
                        "doc_id": doc_id,
                        "page": page_num,
                        "chunk_index": chunk_index,
                        "char_count": len(chunk_text),
                    }
                })
                chunk_index += 1

    return chunks


def _recursive_split(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split text using a hierarchy of separators:
    \n\n (paragraphs) → \n (lines) → '. ' (sentences) → ' ' (words)
    """
    separators = ["\n\n", "\n", ". ", " ", ""]

    for sep in separators:
        if sep == "":
            # Base case: hard split
            return _hard_split(text, chunk_size, overlap)

        parts = text.split(sep)
        if len(parts) > 1:
            return _merge_parts(parts, sep, chunk_size, overlap)

    return [text]


def _merge_parts(parts: List[str], sep: str, chunk_size: int, overlap: int) -> List[str]:
    chunks = []
    current = ""

    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # Start new chunk with overlap from end of last chunk
            if current and overlap > 0:
                overlap_text = current[-overlap:]
                current = overlap_text + sep + part if overlap_text else part
            else:
                current = part

    if current:
        chunks.append(current)

    return chunks


def _hard_split(text: str, chunk_size: int, overlap: int) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks
