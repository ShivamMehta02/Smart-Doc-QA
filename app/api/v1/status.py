from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db import crud
from app.schemas.response import JobStatusResponse
from app.core.exceptions import JobNotFoundError, AppBaseException

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Check the status of a background document processing job.
    Returns status ("queued", "running", "done", "failed") and progress (0-100).
    """
    try:
        job = await crud.get_job(db, job_id)
        if not job:
            raise JobNotFoundError(job_id)
            
        return JobStatusResponse(
            job_id=job.id,
            doc_id=str(job.doc_id),
            status=job.status,
            progress=job.progress,
            error_msg=job.error_msg
        )
    except AppBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
