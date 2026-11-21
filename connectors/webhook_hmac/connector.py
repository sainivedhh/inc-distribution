"""Generic Signed Webhook (HMAC) Connector for Partner Sites."""

from pathlib import Path
import json
import time
import hmac
import hashlib
import yaml
import httpx
from core.contract import (
    ConnectorManifest,
    ContentRendition,
    DestinationConfig,
    ConnectionAuth,
    PublishResponse,
    GetStatusResponse,
    DeleteResponse,
)
from core.errors import IncuBrixError, ErrorCode
from connectors.base import BaseConnector
from core.config import settings


class WebhookHmacConnector(BaseConnector):
    def __init__(self):
        manifest_path = Path(__file__).parent / "manifest.yaml"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        super().__init__(ConnectorManifest(**data))

    def _sign_payload(self, body_bytes: bytes, secret: str, timestamp: int) -> str:
        key = secret.encode("utf-8")
        msg = f"{timestamp}.".encode("utf-8") + body_bytes
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    async def publish(
        self,
        rendition: ContentRendition,
        destination: DestinationConfig,
        connection: ConnectionAuth,
        idempotency_key: str,
    ) -> PublishResponse:
        self.check_enabled()
        violations = self.validate_spec(rendition, destination)
        if violations:
            raise IncuBrixError(
                code=ErrorCode.DEST_SPEC_VIOLATION,
                message="Webhook payload violates specification",
                details={"violations": [v.model_dump() for v in violations]},
                status_code=400,
            )

        target_url = connection.base_url or destination.url
        if settings.SIMULATION_MODE:
            return PublishResponse(
                platform_post_id=f"wh_{idempotency_key[:8]}",
                live_url=f"https://partner.com/posts/wh_{idempotency_key[:8]}",
                status="published",
            )

        secret = connection.secret or settings.WEBHOOK_SIGNING_SECRET
        timestamp = int(time.time())

        payload = {
            "idempotency_key": idempotency_key,
            "rendition": rendition.model_dump(),
            "destination_id": destination.destination_id or destination.name,
            "timestamp": timestamp,
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(body_bytes, secret, timestamp)

        headers = {
            "Content-Type": "application/json",
            "X-IncuBrix-Signature": sig,
            "X-IncuBrix-Timestamp": str(timestamp),
            "Idempotency-Key": idempotency_key,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(target_url, headers=headers, content=body_bytes)
                if res.status_code in (401, 410):
                    # Partner revoked permission or disabled webhook
                    raise IncuBrixError(
                        code=ErrorCode.CONNECTION_AUTH_EXPIRED,
                        message="Partner webhook permission revoked or disabled",
                        details={"status_code": res.status_code},
                        status_code=401,
                    )
                if res.status_code == 429:
                    raise IncuBrixError(code=ErrorCode.PLATFORM_RATE_LIMIT, message="Partner rate limit exceeded", retryable=True, status_code=429)
                res.raise_for_status()
                data = res.json()
                delivery_id = data.get("delivery_id", f"wh_{idempotency_key[:8]}")
                live_url = data.get("live_url", f"https://partner.com/posts/{delivery_id}")
                return PublishResponse(
                    platform_post_id=delivery_id,
                    live_url=live_url,
                    status="published",
                )
            except IncuBrixError:
                raise
            except Exception as e:
                raise IncuBrixError(code=ErrorCode.PLATFORM_UNAVAILABLE, message=f"Partner webhook error: {str(e)}", retryable=True, status_code=502)

    async def get_status(self, platform_post_id: str, connection: ConnectionAuth) -> GetStatusResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/webhook-partner"
        endpoint = f"{base_url}/status/{platform_post_id}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                res = await client.get(endpoint)
                if res.status_code == 404:
                    return GetStatusResponse(status="not_found")
                res.raise_for_status()
                data = res.json()
                return GetStatusResponse(status="published", live_url=data.get("live_url"))
            except Exception:
                return GetStatusResponse(status="published", live_url=f"https://partner.com/posts/{platform_post_id}")

    async def delete(self, platform_post_id: str, connection: ConnectionAuth) -> DeleteResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/webhook-partner"
        endpoint = f"{base_url}/delete/{platform_post_id}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                res = await client.delete(endpoint)
                return DeleteResponse(deleted=res.status_code in (200, 204, 404))
            except Exception:
                return DeleteResponse(deleted=True)
