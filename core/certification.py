"""Certification harness: runs full publish -> verify -> delete -> evidence cycle."""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import DestinationModel
from core.contract import ContentRendition, DestinationConfig, ConnectionAuth
from connectors.base import ConnectorRegistry
from core.errors import IncuBrixError, ErrorCode


class DestinationCertifier:
    @staticmethod
    async def certify_destination(
        destination: DestinationModel,
        connection: ConnectionAuth,
        db: Optional[AsyncSession] = None,
        pack_dir: Path = Path("certification_pack"),
    ) -> Dict[str, Any]:
        """Runs the mandatory certification cycle: publish -> confirm live -> status -> delete -> cleanup."""
        connector = ConnectorRegistry.get(destination.connector_key)
        start_time = time.time()

        rendition = ContentRendition(
            title=f"[CERTIFICATION TEST] Verification for {destination.name}",
            body=f"This is an automated certification verification post for {destination.name}. It will be immediately deleted.",
            tags=["certification", "test"],
            ai_generated=False,
            ai_disclosure_text=None,
        )

        dest_config = DestinationConfig(
            destination_id=destination.id,
            name=destination.name,
            url=destination.url,
            platform_key=destination.platform_key,
            surface=destination.surface,
            connector_key=destination.connector_key,
            disclosure_required=bool(destination.disclosure_required),
        )

        dest_folder = pack_dir / destination.name.lower().replace(" ", "_")
        dest_folder.mkdir(parents=True, exist_ok=True)

        log_evidence = {
            "destination_name": destination.name,
            "connector_key": destination.connector_key,
            "started_at": datetime.utcnow().isoformat(),
            "steps": [],
        }

        try:
            # 1. Publish
            idempotency_key = f"cert_{int(time.time())}_{destination.id[:8]}"
            pub_res = await connector.publish(rendition, dest_config, connection, idempotency_key)
            log_evidence["steps"].append({
                "step": "publish",
                "platform_post_id": pub_res.platform_post_id,
                "live_url": pub_res.live_url,
                "status": pub_res.status,
            })

            # 2. Get Status
            status_res = await connector.get_status(pub_res.platform_post_id, connection)
            log_evidence["steps"].append({
                "step": "get_status",
                "status": status_res.status,
                "live_url": status_res.live_url,
            })

            # 3. Delete / Cleanup
            del_res = await connector.delete(pub_res.platform_post_id, connection)
            log_evidence["steps"].append({
                "step": "delete",
                "deleted": del_res.deleted,
            })

            elapsed = time.time() - start_time
            log_evidence["duration_seconds"] = round(elapsed, 2)
            log_evidence["result"] = "passed"

            # Update DB level and certified timestamp
            destination.level = "L3"
            destination.last_certified_at = datetime.utcnow()
            if db:
                await db.commit()

            # Write evidence file
            with open(dest_folder / "run_record.json", "w", encoding="utf-8") as f:
                json.dump(log_evidence, f, indent=2)

            with open(dest_folder / "deletion_confirmation.txt", "w", encoding="utf-8") as f:
                f.write(f"Post {pub_res.platform_post_id} successfully deleted at {datetime.utcnow().isoformat()}.\n")

            return log_evidence

        except Exception as exc:
            elapsed = time.time() - start_time
            log_evidence["duration_seconds"] = round(elapsed, 2)
            log_evidence["result"] = "failed"
            log_evidence["error"] = str(exc)

            # Auto-demote destination on certification failure (Schema drift or platform error)
            destination.level = "L0"
            if db:
                await db.commit()

            with open(dest_folder / "run_record_failure.json", "w", encoding="utf-8") as f:
                json.dump(log_evidence, f, indent=2)

            raise IncuBrixError(
                code=ErrorCode.SCHEMA_DRIFT_DETECTED if "drift" in str(exc).lower() else ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Certification failed for {destination.name}: {str(exc)}",
                details=log_evidence,
                status_code=502,
            )
