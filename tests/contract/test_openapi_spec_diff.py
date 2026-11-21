import yaml
import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app


@pytest.mark.asyncio
async def test_openapi_spec_matches_running_service():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/openapi.json")
        assert res.status_code == 200
        live_spec = res.json()

    with open("openapi.yaml", "r", encoding="utf-8") as f:
        file_spec = yaml.safe_load(f)

    # Check major structural keys and paths match exactly
    assert live_spec["openapi"] == file_spec["openapi"]
    assert set(live_spec["paths"].keys()) == set(file_spec["paths"].keys())
    for path, path_obj in live_spec["paths"].items():
        assert set(path_obj.keys()) == set(file_spec["paths"][path].keys())
