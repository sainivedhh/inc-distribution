import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app
from core.logging import redact_value


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "X-Correlation-Id" in resp.headers


@pytest.mark.asyncio
async def test_ready_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["checks"]["database"] == "ok"


@pytest.mark.asyncio
async def test_correlation_id_echo():
    custom_id = "test-corr-id-12345"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health", headers={"X-Correlation-Id": custom_id})
        assert resp.status_code == 200
        assert resp.headers["X-Correlation-Id"] == custom_id


def test_secrets_redaction():
    payload = {
        "user": "test_user",
        "api_key": "secret_key_abcdef123456",
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token",
        "nested": {
            "token": "tok_12345",
            "normal_field": "hello world",
            "msg": "Here is my secret=xyz789 to authenticate"
        }
    }
    redacted = redact_value(payload)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["nested"]["token"] == "[REDACTED]"
    assert redacted["nested"]["normal_field"] == "hello world"
    assert "secret=[REDACTED]" in redacted["nested"]["msg"]
