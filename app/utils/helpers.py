import hashlib
import pathlib
from typing import Optional
from app.core.config import settings
from app.core.exceptions import UnsupportedFileTypeError, FileTooLargeError


def compute_sha256(file_bytes: bytes) -> str:
    """SHA-256 hash for deduplication — same file never processed twice."""
    return hashlib.sha256(file_bytes).hexdigest()


def validate_file(filename: str, file_bytes: bytes) -> None:
    """Raise typed exceptions for unsupported or oversized files."""
    ext = pathlib.Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(filename)
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise FileTooLargeError(size_mb, settings.MAX_FILE_SIZE_MB)


def count_tokens_approx(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 chars. Used to stay within model limits."""
    return len(text) // 4


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    max_chars = max_tokens * 4
    return text[:max_chars] if len(text) > max_chars else text


def safe_str(value: Optional[str], fallback: str = "") -> str:
    return value.strip() if value else fallback
