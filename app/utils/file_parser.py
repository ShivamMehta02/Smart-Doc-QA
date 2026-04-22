import io
import pathlib
from typing import List, Dict, Any
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from app.core.exceptions import CorruptFileError
from app.core.logging import get_logger

logger = get_logger(__name__)


def parse_file(filename: str, file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Returns list of pages: [{page: int, text: str}]
    Supports PDF and DOCX.
    """
    ext = pathlib.Path(filename).suffix.lower()
    try:
        if ext == ".pdf":
            return _parse_pdf(file_bytes)
        elif ext == ".docx":
            return _parse_docx(file_bytes)
        else:
            raise CorruptFileError(filename)
    except CorruptFileError:
        raise
    except Exception as e:
        logger.error("file_parse_failed", filename=filename, error=str(e))
        raise CorruptFileError(filename)


def _parse_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
    pages = []
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": page_num + 1, "text": text})
    doc.close()
    return pages


def _parse_docx(file_bytes: bytes) -> List[Dict[str, Any]]:
    pages = []
    doc = DocxDocument(io.BytesIO(file_bytes))
    current_text = []
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if text:
            current_text.append(text)
        # Simulate pages every 40 paragraphs
        if (i + 1) % 40 == 0 and current_text:
            pages.append({"page": len(pages) + 1, "text": "\n".join(current_text)})
            current_text = []
    if current_text:
        pages.append({"page": len(pages) + 1, "text": "\n".join(current_text)})
    return pages
