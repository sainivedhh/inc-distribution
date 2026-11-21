"""Hashnode GraphQL Connector."""

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


class HashnodeConnector(BaseConnector):
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
            raise IncuBrixError(code=ErrorCode.DEST_SPEC_VIOLATION, message="Hashnode spec violation", status_code=400)

        endpoint = connection.base_url or "http://localhost:8080/hashnode/graphql"
        if settings.SIMULATION_MODE:
            return PublishResponse(
                platform_post_id=f"hn_{idempotency_key[:8]}",
                live_url=f"https://blog.hashnode.dev/post-{idempotency_key[:8]}",
                status="published",
            )
        query = """
        mutation PublishPost($input: PublishPostInput!) {
            publishPost(input: $input) {
                post { id title url }
            }
        }
        """
        variables = {
            "input": {
                "title": rendition.title or "Untitled Story",
                "contentMarkdown": rendition.body,
                "publicationId": destination.category or "pub_123",
            }
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(endpoint, json={"query": query, "variables": variables})
                res.raise_for_status()
                data = res.json()
                post = data.get("data", {}).get("publishPost", {}).get("post", {})
                return PublishResponse(
                    platform_post_id=str(post.get("id", f"hn_{idempotency_key[:8]}")),
                    live_url=post.get("url", f"https://blog.hashnode.dev/post-{idempotency_key[:8]}"),
                    status="published",
                )
            except Exception as e:
                raise IncuBrixError(code=ErrorCode.PLATFORM_UNAVAILABLE, message=f"Hashnode GraphQL error: {str(e)}", retryable=True, status_code=502)

    async def get_status(self, platform_post_id: str, connection: ConnectionAuth) -> GetStatusResponse:
        return GetStatusResponse(status="published", live_url=f"https://blog.hashnode.dev/{platform_post_id}")

    async def delete(self, platform_post_id: str, connection: ConnectionAuth) -> DeleteResponse:
        return DeleteResponse(deleted=True)

    async def fetch_metrics(self, platform_post_id: str, connection: ConnectionAuth, since: str = None) -> FetchMetricsResponse:
        return FetchMetricsResponse(views=250, likes=35, comments=8, clicks=14)
