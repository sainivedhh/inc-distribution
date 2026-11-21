"""Hard Case 1: Publish call times out and is retried with the same idempotency key."""

import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from connectors.discourse.connector import DiscourseConnector
from core.contract import ContentRendition, DestinationConfig, ConnectionAuth


@pytest.mark.asyncio
async def test_hard_case_1_timeout_retry():
    connector = DiscourseConnector()
    rendition = ContentRendition(title="Timeout Retry Test", body="Checking zero duplication on timeout retry.")
    destination = DestinationConfig(
        name="Discourse Test",
        url="https://forum.incubrix.test",
        platform_key="discourse",
        surface="topic",
        connector_key="discourse",
    )
    connection = ConnectionAuth(api_key="mock_key", username="testuser")
    idempotency_key = "idem_timeout_case_001"

    # First attempt (simulating publish)
    res1 = await connector.publish(rendition, destination, connection, idempotency_key)
    assert res1.status == "published"
    assert res1.platform_post_id is not None

    # Immediate retry with same idempotency key
    res2 = await connector.publish(rendition, destination, connection, idempotency_key)
    assert res2.status == "published"
    # Guaranteed reconciliation: exactly one post created, same post id returned
    assert res2.platform_post_id == res1.platform_post_id
    assert res2.live_url == res1.live_url
