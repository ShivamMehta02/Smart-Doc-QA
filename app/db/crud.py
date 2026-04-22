import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.models import Document, Chunk, Job, Conversation, DocumentStatus, JobStatus


# ── Documents ─────────────────────────────────────────────────────────────────

async def create_document(db: AsyncSession, filename: str, file_hash: str, file_size: int) -> Document:
    doc = Document(filename=filename, original_filename=filename, file_hash=file_hash, file_size_bytes=file_size)
    db.add(doc)
    await db.flush()
    return doc


async def get_document(db: AsyncSession, doc_id: str) -> Optional[Document]:
    result = await db.execute(select(Document).where(Document.id == uuid.UUID(doc_id)))
    return result.scalar_one_or_none()


async def get_document_by_hash(db: AsyncSession, file_hash: str) -> Optional[Document]:
    result = await db.execute(select(Document).where(Document.file_hash == file_hash))
    return result.scalar_one_or_none()


async def list_documents(db: AsyncSession, skip: int = 0, limit: int = 20) -> List[Document]:
    result = await db.execute(select(Document).offset(skip).limit(limit).order_by(Document.created_at.desc()))
    return result.scalars().all()


async def update_document_status(db: AsyncSession, doc_id: str, status: DocumentStatus,
                                  page_count: int = None, chunk_count: int = None, error_msg: str = None):
    values = {"status": status}
    if page_count is not None: values["page_count"] = page_count
    if chunk_count is not None: values["chunk_count"] = chunk_count
    if error_msg is not None: values["error_msg"] = error_msg
    await db.execute(update(Document).where(Document.id == uuid.UUID(doc_id)).values(**values))


async def delete_document(db: AsyncSession, doc_id: str):
    doc = await get_document(db, doc_id)
    if doc:
        await db.delete(doc)


# ── Chunks ────────────────────────────────────────────────────────────────────

async def create_chunks_bulk(db: AsyncSession, doc_id: str, chunks_data: list[dict]):
    chunks = [
        Chunk(doc_id=uuid.UUID(doc_id), text=c["text"], page=c.get("page"),
              chunk_index=c["chunk_index"], chunk_metadata=c.get("metadata", {}))
        for c in chunks_data
    ]
    db.add_all(chunks)
    await db.flush()
    return chunks


async def get_chunks_by_doc(db: AsyncSession, doc_id: str) -> List[Chunk]:
    result = await db.execute(select(Chunk).where(Chunk.doc_id == uuid.UUID(doc_id)).order_by(Chunk.chunk_index))
    return result.scalars().all()


# ── Jobs ──────────────────────────────────────────────────────────────────────

async def create_job(db: AsyncSession, job_id: str, doc_id: str) -> Job:
    job = Job(id=job_id, doc_id=uuid.UUID(doc_id))
    db.add(job)
    await db.flush()
    return job


async def get_job(db: AsyncSession, job_id: str) -> Optional[Job]:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def update_job(db: AsyncSession, job_id: str, status: JobStatus = None,
                     progress: int = None, error_msg: str = None):
    values = {}
    if status is not None: values["status"] = status
    if progress is not None: values["progress"] = progress
    if error_msg is not None: values["error_msg"] = error_msg
    if values:
        await db.execute(update(Job).where(Job.id == job_id).values(**values))


# ── Conversations ─────────────────────────────────────────────────────────────

async def create_conversation(db: AsyncSession, doc_id: str) -> Conversation:
    conv = Conversation(doc_id=uuid.UUID(doc_id), messages=[])
    db.add(conv)
    await db.flush()
    return conv


async def get_conversation(db: AsyncSession, conv_id: str) -> Optional[Conversation]:
    result = await db.execute(select(Conversation).where(Conversation.id == uuid.UUID(conv_id)))
    return result.scalar_one_or_none()


async def append_message(db: AsyncSession, conv_id: str, role: str, content: str,
                          sources: list = None, confidence: float = None):
    conv = await get_conversation(db, conv_id)
    if not conv:
        return
    messages = list(conv.messages or [])
    messages.append({"role": role, "content": content, "sources": sources or [], "confidence": confidence})
    await db.execute(update(Conversation).where(Conversation.id == uuid.UUID(conv_id)).values(messages=messages))
