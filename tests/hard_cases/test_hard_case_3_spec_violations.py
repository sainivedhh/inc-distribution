"""Hard Case 3: Title or body longer than allowed; unsupported media."""

import pytest
from connectors.discourse.connector import DiscourseConnector
from core.contract import ContentRendition, DestinationConfig, MediaItem
from core.errors import IncuBrixError, ErrorCode


@pytest.mark.asyncio
async def test_hard_case_3_spec_violations():
    connector = DiscourseConnector()
    destination = DestinationConfig(
        name="Discourse Test",
        url="https://forum.incubrix.test",
        platform_key="discourse",
        surface="topic",
        connector_key="discourse",
    )

    # 1. Title exceeding 255 chars
    rendition_long_title = ContentRendition(
        title="T" * 300,
        body="Normal body",
    )
    val_resp = await connector.validate(rendition_long_title, destination)
    assert val_resp.ok is False
    assert any(v.field == "title" and v.rule == "title_max_chars" for v in val_resp.violations)

    # 2. Unsupported media type (e.g. audio on discourse topic)
    rendition_unsupported_media = ContentRendition(
        title="Valid Title",
        body="Valid body content",
        media=[MediaItem(type="audio", url="https://cdn.incubrix.com/audio.mp3")]
    )
    val_resp_media = await connector.validate(rendition_unsupported_media, destination)
    assert val_resp_media.ok is False
    assert any("media" in v.field and "audio" in v.message for v in val_resp_media.violations)
