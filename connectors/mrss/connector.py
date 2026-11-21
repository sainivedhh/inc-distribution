"""MRSS Video Feed Connector."""

from pathlib import Path
import yaml
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


class MrssConnector(BaseConnector):
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
            raise IncuBrixError(code=ErrorCode.DEST_SPEC_VIOLATION, message="MRSS feed spec violation", status_code=400)

        # In MRSS feed generation, publishing renders entry to feed XML
        feed_item_id = f"mrss_{idempotency_key[:8]}"
        return PublishResponse(
            platform_post_id=feed_item_id,
            live_url=f"https://feeds.incubrix.com/mrss/{destination.destination_id or 'main'}#{feed_item_id}",
            status="published",
        )

    async def get_status(self, platform_post_id: str, connection: ConnectionAuth) -> GetStatusResponse:
        return GetStatusResponse(status="published")

    async def delete(self, platform_post_id: str, connection: ConnectionAuth) -> DeleteResponse:
        return DeleteResponse(deleted=True)
