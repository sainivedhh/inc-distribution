"""Atomic Idempotency and Job Processing Manager."""

import hashlib
import json
import uuid
import time
import hmac
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models import JobModel, IdempotencyKeyRecord, PublicationRecord
from core.errors import IncuBrixError, ErrorCode
from core.config import settings
from connectors.base import ConnectorRegistry
from core.contract import ContentRendition, DestinationConfig, ConnectionAuth
import httpx


class SafeExecutionManager:
    @staticmethod
    def compute_request_hash(payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    async def reserve_idempotency_key(
        cls,
        db: AsyncSession,
        idempotency_key: str,
        payload: Dict[str, Any],
    ) -> Optional[JobModel]:
        """Atomically reserves an idempotency key. Returns existing job if duplicate request."""
        req_hash = cls.compute_request_hash(payload)
        record = await db.get(IdempotencyKeyRecord, idempotency_key)
        if record:
            if record.request_hash != req_hash:
                raise IncuBrixError(
                    code=ErrorCode.IDEMPOTENCY_KEY_REUSED,
                    message="Idempotency key was previously used with a different request payload.",
                    status_code=409,
                )
            # Same key and same payload: return existing job
            if record.job_id:
                job = await db.get(JobModel, record.job_id)
                return job

        # Create new idempotency reservation
        new_record = IdempotencyKeyRecord(
            key=idempotency_key,
            request_hash=req_hash,
            status="reserved",
        )
        db.add(new_record)
        await db.commit()
        return None

    @classmethod
    async def create_job(
        cls,
        db: AsyncSession,
        job_type: str,
        payload: Dict[str, Any],
        idempotency_key: str,
        callback_url: Optional[str] = None,
    ) -> JobModel:
        job = JobModel(
            id=str(uuid.uuid4()),
            job_type=job_type,
            status="queued",
            progress=0,
            payload=payload,
            callback_url=callback_url,
        )
        db.add(job)
        # Link idempotency record
        record = await db.get(IdempotencyKeyRecord, idempotency_key)
        if record:
            record.job_id = job.id
            record.status = "queued"
        await db.commit()
        await db.refresh(job)
        return job

    @classmethod
    async def dispatch_webhook_callback(cls, job: JobModel):
        if not job.callback_url:
            return
        body = {
            "job_id": job.id,
            "status": job.status,
            "result": job.result,
            "error": job.error,
            "timestamp": int(time.time()),
        }
        body_bytes = json.dumps(body).encode("utf-8")
        secret = settings.WEBHOOK_SIGNING_SECRET.encode("utf-8")
        signature = hmac.new(secret, body_bytes, hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-IncuBrix-Signature": signature,
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                await client.post(job.callback_url, headers=headers, content=body_bytes)
            except Exception:
                pass
