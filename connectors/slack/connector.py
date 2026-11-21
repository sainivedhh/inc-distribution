"""Slack App Community Connector."""

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


class SlackConnector(BaseConnector):
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
            raise IncuBrixError(code=ErrorCode.DEST_SPEC_VIOLATION, message="Slack message spec violation", status_code=400)

        endpoint = connection.base_url or "http://localhost:8080/slack/api/chat.postMessage"
        if settings.SIMULATION_MODE:
            return PublishResponse(
                platform_post_id="1234567890.123456",
                live_url="https://slack.com/archives/general/p1234567890123456",
                status="published",
            )
        channel = destination.category or "general"
        text = f"*{rendition.title}*\n{rendition.body}" if rendition.title else rendition.body

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(endpoint, json={"channel": channel, "text": text})
                res.raise_for_status()
                data = res.json()
                ts = data.get("ts", "123.456")
                return PublishResponse(
                    platform_post_id=ts,
                    live_url=f"https://slack.com/archives/{channel}/p{ts.replace('.', '')}",
                    status="published",
                )
            except Exception as e:
                raise IncuBrixError(code=ErrorCode.PLATFORM_UNAVAILABLE, message=f"Slack API error: {str(e)}", retryable=True, status_code=502)

    async def get_status(self, platform_post_id: str, connection: ConnectionAuth) -> GetStatusResponse:
        return GetStatusResponse(status="published")

    async def delete(self, platform_post_id: str, connection: ConnectionAuth) -> DeleteResponse:
        return DeleteResponse(deleted=True)
