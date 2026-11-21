"""Lemmy Protocol Connector."""

from pathlib import Path
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


class LemmyConnector(BaseConnector):
    def __init__(self):
        manifest_path = Path(__file__).parent / "manifest.yaml"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        super().__init__(ConnectorManifest(**data))

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
                message="Lemmy post violates destination specification",
                details={"violations": [v.model_dump() for v in violations]},
                status_code=400,
            )

        base_url = connection.base_url or destination.url.rstrip("/")
        if settings.SIMULATION_MODE and not base_url.startswith("http"):
            base_url = "http://localhost:8080/lemmy"

        if settings.SIMULATION_MODE and "8080" not in base_url:
            return PublishResponse(
                platform_post_id=f"lemmy_{idempotency_key[:8]}",
                live_url=f"{base_url}/post/{idempotency_key[:8]}",
                status="published",
            )

        jwt = connection.jwt_token or connection.api_key or "mock-lemmy-jwt-token-abcdef123"
        endpoint = f"{base_url}/api/v3/post"
        headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
        payload = {
            "name": rendition.title or "Untitled Post",
            "body": rendition.body,
            "community_id": int(destination.category) if destination.category and destination.category.isdigit() else 1,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(endpoint, headers=headers, json=payload)
                if res.status_code == 401:
                    raise IncuBrixError(code=ErrorCode.CONNECTION_AUTH_EXPIRED, message="Lemmy JWT expired or invalid", status_code=401)
                if res.status_code == 429:
                    raise IncuBrixError(code=ErrorCode.PLATFORM_RATE_LIMIT, message="Lemmy rate limited", retryable=True, status_code=429)
                res.raise_for_status()
                data = res.json()
                post_id = str(data["post_view"]["post"]["id"])
                return PublishResponse(
                    platform_post_id=post_id,
                    live_url=f"{base_url}/post/{post_id}",
                    status="published",
                )
            except IncuBrixError:
                raise
            except Exception as e:
                raise IncuBrixError(code=ErrorCode.PLATFORM_UNAVAILABLE, message=f"Lemmy API error: {str(e)}", retryable=True, status_code=502)

    async def get_status(self, platform_post_id: str, connection: ConnectionAuth) -> GetStatusResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/lemmy"
        if settings.SIMULATION_MODE:
            return GetStatusResponse(status="published", live_url=f"{base_url}/post/{platform_post_id}")

        endpoint = f"{base_url}/api/v3/post?id={platform_post_id}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(endpoint)
            if res.status_code == 404:
                return GetStatusResponse(status="not_found")
            res.raise_for_status()
            data = res.json()
            deleted = data.get("post_view", {}).get("post", {}).get("deleted", False)
            return GetStatusResponse(
                status="deleted" if deleted else "published",
                live_url=f"{base_url}/post/{platform_post_id}",
            )

    async def delete(self, platform_post_id: str, connection: ConnectionAuth) -> DeleteResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/lemmy"
        if settings.SIMULATION_MODE:
            return DeleteResponse(deleted=True)

        jwt = connection.jwt_token or connection.api_key or "mock-lemmy-jwt-token-abcdef123"
        endpoint = f"{base_url}/api/v3/post/delete"
        headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
        payload = {"post_id": int(platform_post_id), "deleted": True}
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(endpoint, headers=headers, json=payload)
            return DeleteResponse(deleted=res.status_code in (200, 204))
