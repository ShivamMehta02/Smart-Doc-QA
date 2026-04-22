import asyncio
import numpy as np
from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.db.models import DocumentStatus, JobStatus
from app.db import crud
from app.utils.file_parser import parse_file
from app.utils.chunking import chunk_pages
from app.services.embedding_service import embed_texts
from app.vectorstore.faiss_store import get_faiss_store
from app.core.logging import get_logger

logger = get_logger(__name__)


def _run_async(coro):
    """Run async code inside Celery sync task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="app.workers.tasks.process_document",
)
def process_document(self: Task, doc_id: str, filename: str, file_bytes_hex: str):
    """
    Background task: parse → chunk → embed → index → update DB.
    
    Uses hex-encoded bytes to pass file content through Redis (Celery serialization).
    Progress is updated at each step so the status endpoint shows live progress.
    """
    job_id = self.request.id
    file_bytes = bytes.fromhex(file_bytes_hex)

    async def _process():
        async with AsyncSessionLocal() as db:
            try:
                # Step 1: Mark running (20%)
                await crud.update_job(db, job_id, status=JobStatus.RUNNING, progress=10)
                await crud.update_document_status(db, doc_id, DocumentStatus.PROCESSING)
                await db.commit()

                # Step 2: Parse file (30%)
                logger.info("parsing_file", doc_id=doc_id, filename=filename)
                pages = parse_file(filename, file_bytes)
                await crud.update_job(db, job_id, progress=30)
                await db.commit()

                # Step 3: Chunk (50%)
                logger.info("chunking", doc_id=doc_id, pages=len(pages))
                chunks = chunk_pages(pages, doc_id)
                await crud.update_job(db, job_id, progress=50)
                await db.commit()

                # Step 4: Store chunks in DB (60%)
                await crud.create_chunks_bulk(db, doc_id, chunks)
                await crud.update_job(db, job_id, progress=60)
                await db.commit()

                # Step 5: Generate embeddings (80%)
                logger.info("embedding", doc_id=doc_id, chunks=len(chunks))
                texts = [c["text"] for c in chunks]
                vectors = embed_texts(texts)
                await crud.update_job(db, job_id, progress=80)
                await db.commit()

                # Step 6: Index in FAISS (90%)
                db_chunks = await crud.get_chunks_by_doc(db, doc_id)
                chunk_ids = [str(c.id) for c in db_chunks]
                store = get_faiss_store(doc_id)
                store.add_vectors(vectors, chunk_ids)
                await crud.update_job(db, job_id, progress=90)
                await db.commit()

                # Step 7: Mark ready (100%)
                await crud.update_document_status(
                    db, doc_id, DocumentStatus.READY,
                    page_count=len(pages), chunk_count=len(chunks)
                )
                await crud.update_job(db, job_id, status=JobStatus.DONE, progress=100)
                await db.commit()
                logger.info("document_processed", doc_id=doc_id, chunks=len(chunks))

            except Exception as e:
                logger.error("document_processing_failed", doc_id=doc_id, error=str(e))
                await crud.update_document_status(db, doc_id, DocumentStatus.FAILED, error_msg=str(e))
                await crud.update_job(db, job_id, status=JobStatus.FAILED, error_msg=str(e))
                await db.commit()
                raise self.retry(exc=e)

    _run_async(_process())
