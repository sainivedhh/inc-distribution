"""Destinations API endpoints for Phase 4 (Configuration-not-code catalogue)."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.models import DestinationModel
from core.errors import IncuBrixError, ErrorCode

router = APIRouter(prefix="/api/v1/destinations", tags=["Destinations Catalogue"])


class DestinationCreate(BaseModel):
    name: str
    url: str
    platform_key: str
    surface: str
    category: Optional[str] = None
    audience_tags: List[str] = Field(default_factory=list)
    language: str = "en"
    geo: Optional[str] = "global"
    est_audience: Optional[int] = 0
    rules_url: Optional[str] = None
    frequency_cap: Optional[str] = "1 per 7 days"
    self_promo_allowed: bool = True
    link_policy: Optional[str] = "allowed"
    disclosure_required: bool = False
    automation_allowed: bool = True
    connector_key: str
    relevance_score: Optional[int] = 3
    relevance_reason: Optional[str] = None
    level: Optional[str] = "L0"


class DestinationResponse(DestinationCreate):
    id: str
    last_certified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=DestinationResponse, status_code=status.HTTP_201_CREATED)
async def create_destination(dest_in: DestinationCreate, db: AsyncSession = Depends(get_db)):
    """Create a new destination row at runtime (zero-code configuration)."""
    # Check duplicate
    stmt = select(DestinationModel).where(
        DestinationModel.url == dest_in.url,
        DestinationModel.platform_key == dest_in.platform_key,
    )
    res = await db.execute(stmt)
    if res.scalars().first():
        raise IncuBrixError(
            code=ErrorCode.INVALID_REQUEST,
            message=f"Destination '{dest_in.url}' on platform '{dest_in.platform_key}' already exists.",
            status_code=409,
        )

    dest = DestinationModel(**dest_in.model_dump())
    db.add(dest)
    await db.commit()
    await db.refresh(dest)
    return dest


@router.get("", response_model=List[DestinationResponse])
async def list_destinations(
    platform_key: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(DestinationModel)
    if platform_key:
        stmt = stmt.where(DestinationModel.platform_key == platform_key)
    if level:
        stmt = stmt.where(DestinationModel.level == level)
    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{destination_id}", response_model=DestinationResponse)
async def get_destination(destination_id: str, db: AsyncSession = Depends(get_db)):
    dest = await db.get(DestinationModel, destination_id)
    if not dest:
        raise IncuBrixError(code=ErrorCode.NOT_FOUND, message=f"Destination {destination_id} not found", status_code=404)
    return dest
