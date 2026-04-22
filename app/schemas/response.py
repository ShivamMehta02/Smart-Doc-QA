from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class UploadResponse(BaseModel):
    doc_id: str
    job_id: str
    filename: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    doc_id: str
    status: str
    progress: int
    error_msg: Optional[str] = None


class SourceReference(BaseModel):
    chunk_id: str
    doc_id: str
    page: Optional[int]
    text_snippet: str


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[SourceReference]
    fallback: bool
    question: str


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[SourceReference]
    fallback: bool
    conversation_id: str
    question: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    page_count: Optional[int]
    chunk_count: Optional[int]
    created_at: Optional[datetime]


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class HealthResponse(BaseModel):
    status: str
    api: str
    database: str
    redis: str
    version: str
