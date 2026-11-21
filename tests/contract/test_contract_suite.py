import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app


@pytest.mark.asyncio
async def test_contract_validate_discourse():
    payload = {
        "rendition": {
            "title": "Discussion Title",
            "body": "This is a meaningful community discussion body.",
            "language": "en"
        },
        "destination": {
            "name": "Discourse AI",
            "url": "https://meta.discourse.org",
            "platform_key": "discourse",
            "surface": "topic",
            "connector_key": "discourse"
        }
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/connector/v1/discourse/validate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["violations"] == []


@pytest.mark.asyncio
async def test_contract_spec_violation_discourse():
    payload = {
        "rendition": {
            "title": "A" * 300,  # exceeds 255 chars
            "body": "Body content",
        },
        "destination": {
            "name": "Discourse Forum",
            "url": "https://meta.discourse.org",
            "platform_key": "discourse",
            "surface": "topic",
            "connector_key": "discourse"
        }
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/connector/v1/discourse/validate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is False
        assert any(v["field"] == "title" for v in data["violations"])


@pytest.mark.asyncio
async def test_contract_publish_simulation_discourse():
    payload = {
        "rendition": {
            "title": "Valid Post Title",
            "body": "Great insights on AI workflows.",
        },
        "destination": {
            "name": "Discourse AI",
            "url": "https://meta.discourse.org",
            "platform_key": "discourse",
            "surface": "topic",
            "connector_key": "discourse"
        },
        "connection": {
            "api_key": "test_api_key",
            "username": "candidate"
        },
        "idempotency_key": "test_idem_001"
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/connector/v1/discourse/publish", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "platform_post_id" in data
        assert "live_url" in data
        assert data["status"] == "published"


@pytest.mark.asyncio
async def test_contract_assisted_tier_pack():
    payload = {
        "rendition": {
            "title": "Manual Submission Title",
            "body": "Content needing review and manual posting",
            "media": [{"type": "image", "url": "https://cdn.incubrix.com/img1.png"}],
            "tags": ["ai", "growth"]
        },
        "destination": {
            "name": "Indie Hackers Manual",
            "url": "https://www.indiehackers.com",
            "platform_key": "assisted",
            "surface": "manual_pack",
            "connector_key": "assisted",
            "automation_allowed": False,
            "disclosure_required": True
        }
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Publish must fail
        pub_res = await client.post(
            "/connector/v1/assisted/publish",
            json={"rendition": payload["rendition"], "destination": payload["destination"], "connection": {}, "idempotency_key": "k1"}
        )
        assert pub_res.status_code == 400
        err = pub_res.json()
        assert err["error"]["code"] == "DEST_SPEC_VIOLATION"

        # build_assist_pack must succeed
        res = await client.post("/connector/v1/assisted/build_assist_pack", json=payload)
        assert res.status_code == 200
        pack = res.json()
        assert "caption" in pack
        assert len(pack["files"]) == 1
        assert len(pack["checklist"]) >= 3
