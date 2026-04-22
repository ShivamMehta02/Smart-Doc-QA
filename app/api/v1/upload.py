from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db import crud
from app.db.models import DocumentStatus
from app.schemas.response import UploadResponse
from app.utils.helpers import compute_sha256, validate_file
from app.core.exceptions import DuplicateDocumentError, AppBaseException
from app.workers.tasks import process_document
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_document(
    file: UploadFile = File(..., description="PDF or DOCX file"),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document for processing.
    
    - Returns immediately with a `job_id`
    - Poll `GET /jobs/{job_id}/status` to track progress
    - Document is ready when status = "ready"
    """
    try:
        file_bytes = await file.read()
        validate_file(file.filename, file_bytes)

        file_hash = compute_sha256(file_bytes)
        existing = await crud.get_document_by_hash(db, file_hash)
        if existing:
            raise DuplicateDocumentError(file_hash)

        doc = await crud.create_document(db, file.filename, file_hash, len(file_bytes))
        await db.commit()

        task = process_document.delay(str(doc.id), file.filename, file_bytes.hex())
        job = await crud.create_job(db, task.id, str(doc.id))
        await db.commit()

        logger.info("upload_accepted", doc_id=str(doc.id), job_id=task.id)
        return UploadResponse(
            doc_id=str(doc.id), job_id=task.id,
            filename=file.filename, status="pending",
            message="Document uploaded. Use job_id to track processing progress."
        )

    except AppBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/", tags=["Documents"])
async def list_documents(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """List all uploaded documents."""
    docs = await crud.list_documents(db, skip=skip, limit=limit)
    return {"documents": [{"id": str(d.id), "filename": d.filename, "status": d.status, "chunk_count": d.chunk_count, "created_at": d.created_at} for d in docs]}


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a document and all its chunks."""
    from app.vectorstore.faiss_store import remove_faiss_store
    await crud.delete_document(db, doc_id)
    remove_faiss_store(doc_id)
    await db.commit()
