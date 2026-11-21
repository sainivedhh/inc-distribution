"""SQLAlchemy Models for Destinations, Jobs, Posts, and Idempotency Records."""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DestinationModel(Base):
    """Destination record exactly matching IncuBrix Appendix A & Catalogue schema."""

    __tablename__ = "destinations"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    url = Column(String(512), nullable=False)
    platform_key = Column(String(64), nullable=False)
    surface = Column(String(64), nullable=False)
    category = Column(String(128), nullable=True)
    audience_tags = Column(JSON, default=list)  # list of tags e.g. ["ai", "saas"]
    language = Column(String(16), default="en")
    geo = Column(String(64), default="global")
    est_audience = Column(Integer, default=0)
    rules_url = Column(String(512), nullable=True)
    frequency_cap = Column(String(64), default="1 per 7 days")
    self_promo_allowed = Column(Boolean, default=True)
    link_policy = Column(String(64), default="allowed")  # allowed, no_links, max_links
    disclosure_required = Column(Boolean, default=False)
    automation_allowed = Column(Boolean, default=True)
    connector_key = Column(String(64), nullable=False)
    relevance_score = Column(Integer, default=3)  # 1 to 5
    relevance_reason = Column(Text, nullable=True)
    level = Column(String(16), default="L0")  # L0, L1, L2, L3, L4
    last_certified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint on normalised URL and platform key to prevent duplicates
    __table_args__ = (UniqueConstraint("url", "platform_key", name="uq_dest_url_platform"),)


class JobModel(Base):
    """Background jobs tracking (Integration Standard point 3)."""

    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(32), default="queued")  # queued, running, succeeded, failed
    progress = Column(Integer, default=0)  # 0 to 100
    job_type = Column(String(64), nullable=False)
    payload = Column(JSON, default=dict)
    result = Column(JSON, nullable=True)
    error = Column(JSON, nullable=True)
    callback_url = Column(String(512), nullable=True)
    callback_signature = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PublicationRecord(BaseModel if False else Base):
    """Tracks published items for frequency caps and idempotency."""

    __tablename__ = "publication_records"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    destination_id = Column(String(64), ForeignKey("destinations.id"), nullable=False)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    platform_post_id = Column(String(255), nullable=True)
    live_url = Column(String(512), nullable=True)
    status = Column(String(32), default="pending")  # pending, published, failed, deleted
    title = Column(String(512), nullable=True)
    body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    published_at = Column(DateTime, nullable=True)


class IdempotencyKeyRecord(Base):
    """Tracks Idempotency keys atomically before work begins."""

    __tablename__ = "idempotency_keys"

    key = Column(String(128), primary_key=True)
    request_hash = Column(String(64), nullable=False)
    job_id = Column(String(64), nullable=True)
    status = Column(String(32), default="in_progress")
    response_body = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
