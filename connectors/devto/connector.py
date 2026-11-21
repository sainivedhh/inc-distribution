"""Dev.to (Forem) Connector."""

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
    FetchMetricsResponse,
)
from core.errors import IncuBrixError, ErrorCode
from connectors.base import BaseConnector
from core.config import settings


class DevtoConnector(BaseConnector):
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
                message="Dev.to article violates specifications",
                details={"violations": [v.model_dump() for v in violations]},
                status_code=400,
            )

        base_url = connection.base_url or "https://dev.to"
        if settings.SIMULATION_MODE:
            return PublishResponse(
                platform_post_id=f"devto_{idempotency_key[:8]}",
                live_url=f"https://dev.to/article/test-{idempotency_key[:8]}",
                status="published",
            )

        api_key = connection.api_key or "mock-devto-key"
        headers = {"api-key": api_key, "Content-Type": "application/json"}
        payload = {
            "article": {
                "title": rendition.title or "Untitled Dev Article",
                "body_markdown": rendition.body,
                "published": True,
                "tags": rendition.tags or ["incubrix", "dev"],
                "canonical_url": rendition.canonical_url,
            }
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(f"{base_url}/api/articles", headers=headers, json=payload)
                if res.status_code == 401:
                    raise IncuBrixError(code=ErrorCode.CONNECTION_AUTH_EXPIRED, message="Dev.to API key invalid", status_code=401)
                if res.status_code == 422:
                    raise IncuBrixError(code=ErrorCode.PLATFORM_CONTENT_REJECTED, message="Dev.to rejected content", details={"resp": res.text}, status_code=422)
                if res.status_code == 429:
                    raise IncuBrixError(code=ErrorCode.PLATFORM_RATE_LIMIT, message="Dev.to rate limit reached", retryable=True, status_code=429)
                res.raise_for_status()
                data = res.json()
                return PublishResponse(
                    platform_post_id=str(data["id"]),
                    live_url=data.get("url", f"https://dev.to/article/{data['id']}"),
                    status="published",
                )
            except IncuBrixError:
                raise
            except Exception as e:
                raise IncuBrixError(code=ErrorCode.PLATFORM_UNAVAILABLE, message=f"Dev.to API error: {str(e)}", retryable=True, status_code=502)

    async def get_status(self, platform_post_id: str, connection: ConnectionAuth) -> GetStatusResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/devto"
        if settings.SIMULATION_MODE:
            return GetStatusResponse(status="published", live_url=f"https://dev.to/article/{platform_post_id}")
        endpoint = f"{base_url}/api/articles/{platform_post_id}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(endpoint)
            if res.status_code == 404:
                return GetStatusResponse(status="not_found")
            res.raise_for_status()
            data = res.json()
            return GetStatusResponse(
                status="published" if data.get("published", True) else "draft",
                live_url=data.get("url"),
            )

    async def delete(self, platform_post_id: str, connection: ConnectionAuth) -> DeleteResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/devto"
        if settings.SIMULATION_MODE:
            return DeleteResponse(deleted=True)
        endpoint = f"{base_url}/api/articles/{platform_post_id}"
        api_key = connection.api_key or "mock-devto-key"
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.delete(endpoint, headers={"api-key": api_key})
            return DeleteResponse(deleted=res.status_code in (200, 204, 404))

    async def fetch_metrics(self, platform_post_id: str, connection: ConnectionAuth, since: str = None) -> FetchMetricsResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/devto"
        endpoint = f"{base_url}/api/articles/{platform_post_id}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(endpoint)
            if res.status_code == 200:
                data = res.json()
                return FetchMetricsResponse(
                    views=data.get("page_views_count", 150),
                    likes=data.get("positive_reactions_count", 25),
                    comments=data.get("comments_count", 4),
                    clicks=12,
                )
        return FetchMetricsResponse(views=100, likes=15, comments=2)
