"""Assisted Tier Connector for communities where automated posting is disallowed."""

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
    BuildAssistPackResponse,
    ChecklistItem,
)
from core.errors import IncuBrixError, ErrorCode
from connectors.base import BaseConnector


class AssistedConnector(BaseConnector):
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
        raise IncuBrixError(
            code=ErrorCode.DEST_SPEC_VIOLATION,
            message="Automated publishing is strictly disallowed on assisted tier destinations. Use build_assist_pack.",
            status_code=400,
        )

    async def get_status(self, platform_post_id: str, connection: ConnectionAuth) -> GetStatusResponse:
        return GetStatusResponse(status="published")

    async def delete(self, platform_post_id: str, connection: ConnectionAuth) -> DeleteResponse:
        return DeleteResponse(deleted=False)

    async def build_assist_pack(
        self,
        rendition: ContentRendition,
        destination: DestinationConfig,
    ) -> BuildAssistPackResponse:
        self.check_enabled()
        files = [m.url for m in (rendition.media or [])]

        caption_parts = []
        if rendition.title:
            caption_parts.append(rendition.title)
        caption_parts.append(rendition.body)
        if rendition.tags:
            caption_parts.append(" ".join([f"#{t}" for t in rendition.tags]))
        if destination.disclosure_required or rendition.ai_generated:
            caption_parts.append(rendition.ai_disclosure_text or "[AI-Assisted Content Disclosure]")

        caption = "\n\n".join(caption_parts)

        checklist = [
            ChecklistItem(rule="frequency_cap", instruction=f"Verify no posts from IncuBrix in {destination.frequency_cap}"),
            ChecklistItem(rule="self_promotion", instruction="Ensure non-promotional discussion tone"),
            ChecklistItem(rule="ai_disclosure", instruction="Confirm AI disclosure is visible in post body"),
            ChecklistItem(rule="manual_submit", instruction=f"Open deep link: {destination.url} and submit manually"),
        ]

        return BuildAssistPackResponse(
            files=files,
            caption=caption,
            deep_link=destination.url,
            checklist=checklist,
        )
