"""Background Jobs Management API conforming to Integration Standard point 3."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.models import JobModel
from core.errors import IncuBrixError, ErrorCode

router = APIRouter(prefix="/api/v1/jobs", tags=["Background Jobs"])


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # queued, running, succeeded, failed
    progress: int  # 0 to 100
    job_type: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """Integration Standard point 3: GET /api/v1/jobs/{job_id}."""
    job = await db.get(JobModel, job_id)
    if not job:
        raise IncuBrixError(code=ErrorCode.NOT_FOUND, message=f"Job '{job_id}' not found.", status_code=404)

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        job_type=job.job_type,
        result=job.result,
        error=job.error,
    )
