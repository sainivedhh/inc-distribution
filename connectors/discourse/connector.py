"""Discourse Native Connector."""

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
from connectors.discourse.errors import map_discourse_error
from core.config import settings


class DiscourseConnector(BaseConnector):
    def __init__(self):
        manifest_path = Path(__file__).parent / "manifest.yaml"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        manifest = ConnectorManifest(**data)
        super().__init__(manifest)

    def _get_headers(self, connection: ConnectionAuth) -> dict:
        api_key = connection.api_key or "mock-key"
        username = connection.username or "system"
        return {
            "Api-Key": api_key,
            "Api-Username": username,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

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
                message="Content violates Discourse destination specifications.",
                details={"violations": [v.model_dump() for v in violations]},
                status_code=400,
            )

        base_url = connection.base_url or destination.url.rstrip("/")
        if settings.SIMULATION_MODE and not base_url.startswith("http"):
            base_url = "http://localhost:8080/discourse"

        # Simulation short-circuit when running against pure simulation
        if settings.SIMULATION_MODE and "localhost:8080" not in base_url and "127.0.0.1:8080" not in base_url:
            return PublishResponse(
                platform_post_id=f"disc_post_{idempotency_key[:8]}",
                live_url=f"{base_url}/t/topic-{idempotency_key[:8]}/1",
                status="published",
            )

        endpoint = f"{base_url}/posts.json"
        headers = self._get_headers(connection)
        payload = {
            "title": rendition.title or "Untitled Discussion",
            "raw": rendition.body,
            "category": int(destination.category) if destination.category and destination.category.isdigit() else None,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(endpoint, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                post_id = str(data.get("id"))
                topic_slug = data.get("topic_slug", f"topic-{post_id}")
                topic_id = data.get("topic_id", post_id)
                live_url = f"{base_url}/t/{topic_slug}/{topic_id}"
                return PublishResponse(
                    platform_post_id=post_id,
                    live_url=live_url,
                    status="published",
                )
            except Exception as exc:
                raise map_discourse_error(exc)

    async def get_status(
        self,
        platform_post_id: str,
        connection: ConnectionAuth,
    ) -> GetStatusResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/discourse"
        if settings.SIMULATION_MODE and "8080" not in base_url:
            return GetStatusResponse(
                status="published",
                live_url=f"{base_url}/t/post/{platform_post_id}",
            )
        if settings.SIMULATION_MODE:
            return GetStatusResponse(
                status="published",
                live_url=f"http://localhost:8080/discourse/t/{platform_post_id}",
            )

        endpoint = f"{base_url}/posts/{platform_post_id}.json"
        headers = self._get_headers(connection)
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                res = await client.get(endpoint, headers=headers)
                if res.status_code == 404:
                    return GetStatusResponse(status="not_found", live_url=None)
                res.raise_for_status()
                data = res.json()
                topic_id = data.get("topic_id")
                return GetStatusResponse(
                    status="published",
                    live_url=f"{base_url}/t/{topic_id}" if topic_id else None,
                )
            except Exception as exc:
                raise map_discourse_error(exc)

    async def delete(
        self,
        platform_post_id: str,
        connection: ConnectionAuth,
    ) -> DeleteResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/discourse"
        if settings.SIMULATION_MODE and "8080" not in base_url:
            return DeleteResponse(deleted=True)
        if settings.SIMULATION_MODE:
            return DeleteResponse(deleted=True)

        endpoint = f"{base_url}/posts/{platform_post_id}.json"
        headers = self._get_headers(connection)
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                res = await client.delete(endpoint, headers=headers)
                if res.status_code in (200, 204, 404):
                    return DeleteResponse(deleted=True)
                res.raise_for_status()
                return DeleteResponse(deleted=True)
            except Exception as exc:
                raise map_discourse_error(exc)

    async def fetch_metrics(
        self,
        platform_post_id: str,
        connection: ConnectionAuth,
        since: str = None,
    ) -> FetchMetricsResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/discourse"
        if settings.SIMULATION_MODE and "8080" not in base_url:
            return FetchMetricsResponse(views=124, likes=14, comments=3, shares=1, saves=2, clicks=8)

        endpoint = f"{base_url}/posts/{platform_post_id}.json"
        headers = self._get_headers(connection)
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                res = await client.get(endpoint, headers=headers)
                res.raise_for_status()
                data = res.json()
                reads = data.get("reads", 0)
                score = data.get("score", 0)
                like_count = 0
                for action in data.get("actions_summary", []):
                    if action.get("id") == 2:  # like action in discourse
                        like_count = action.get("count", 0)
                return FetchMetricsResponse(
                    views=reads,
                    likes=like_count,
                    comments=data.get("reply_count", 0),
                    shares=0,
                    saves=data.get("bookmarked", 0) if isinstance(data.get("bookmarked"), int) else 0,
                    clicks=data.get("incoming_link_count", 0),
                )
            except Exception as exc:
                raise map_discourse_error(exc)
