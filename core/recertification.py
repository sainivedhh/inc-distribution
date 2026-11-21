"""Destination Recertification Scheduler (Phase 11 Outstanding)."""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models import DestinationModel
from core.certification import DestinationCertifier
from core.contract import ConnectionAuth


class RecertificationScheduler:
    @staticmethod
    async def find_stale_destinations(
        db: AsyncSession,
        max_age_days: int = 30,
        current_time: datetime = None,
    ) -> List[DestinationModel]:
        now = current_time or datetime.utcnow()
        threshold = now - timedelta(days=max_age_days)
        stmt = select(DestinationModel).where(
            DestinationModel.level.in_(["L3", "L4"]),
            (DestinationModel.last_certified_at < threshold) | (DestinationModel.last_certified_at.is_(None)),
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def run_recertification_cycle(
        cls,
        db: AsyncSession,
        connection: ConnectionAuth,
        current_time: datetime = None,
    ) -> List[Dict[str, Any]]:
        stale_destinations = await cls.find_stale_destinations(db, max_age_days=30, current_time=current_time)
        results = []
        for dest in stale_destinations:
            try:
                cert_result = await DestinationCertifier.certify_destination(dest, connection, db=db)
                results.append({"destination_id": dest.id, "name": dest.name, "status": "recertified"})
            except Exception as e:
                # Failing destination is automatically demoted and excluded
                dest.level = "L0"
                await db.commit()
                results.append({
                    "destination_id": dest.id,
                    "name": dest.name,
                    "status": "failed_and_demoted",
                    "alert": f"CRITICAL: Destination {dest.name} failed recertification and was demoted to L0: {str(e)}"
                })
        return results
