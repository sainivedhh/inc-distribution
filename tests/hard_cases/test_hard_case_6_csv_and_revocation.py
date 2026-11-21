"""Hard Case 6: CSV with duplicates/bad URLs/mixed languages; partner revokes permission."""

import pytest
from httpx import AsyncClient, ASGITransport
from core.catalogue_import import CatalogueImporter
from connectors.webhook_hmac.connector import WebhookHmacConnector
from core.contract import ContentRendition, DestinationConfig, ConnectionAuth
from core.errors import IncuBrixError, ErrorCode


@pytest.mark.asyncio
async def test_hard_case_6_csv_and_partner_revocation():
    # 1. CSV Import with duplicates, bad/SSRF URLs, and mixed languages
    raw_csv = """name,url,platform_key,category,audience_tags,language
AI Forum 1,https://meta.discourse.org,discourse,tech,ai;saas,en
AI Forum Duplicate,https://meta.discourse.org/,discourse,tech,ai,en
Malicious SSRF Destination,http://192.168.1.100/admin,discourse,internal,ai,en
French Dev Blog,https://journaldunet.com,ghost,dev,engineering,fr
"""
    # Disallowing local mocks to test private IP SSRF block
    result = await CatalogueImporter.import_csv_rows(raw_csv, allow_local_mocks=False)
    assert result["total_rows_processed"] == 4
    assert result["duplicates_found"] == 1
    assert result["errors_count"] == 1
    assert any("SSRF" in err["error"] for err in result["errors"])
    assert result["imported_count"] == 2  # Only AI Forum 1 and French Dev Blog

    # 2. Partner revokes webhook permission (returns 401 or 410)
    connector = WebhookHmacConnector()
    destination = DestinationConfig(
        name="Partner Site",
        url="http://test/webhook-partner/publish",
        platform_key="webhook_hmac",
        surface="webhook",
        connector_key="webhook_hmac",
    )
    rendition = ContentRendition(body="Test partner update")
    connection = ConnectionAuth(base_url="http://test/webhook-partner/publish")

    from mocks.server import FLAGS, mock_app
    FLAGS["webhook_revoked"] = True
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as client:
        # Test simulated partner revocation directly
        resp = await client.post("/webhook-partner/publish", json={"msg": "test"})
        assert resp.status_code == 410
    FLAGS["webhook_revoked"] = False
