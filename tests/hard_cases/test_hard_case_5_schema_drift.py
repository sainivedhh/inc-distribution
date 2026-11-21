"""Hard Case 5: Platform renames a field in its API -> certification fails & destination demoted."""

import pytest
from core.models import DestinationModel
from core.certification import DestinationCertifier
from core.contract import ConnectionAuth
from core.errors import IncuBrixError, ErrorCode


class DriftingConnector:
    key = "drift_test"
    async def publish(self, *args, **kwargs):
        # Platform renamed 'id' field in API to 'identifier_token' -> causes schema drift failure
        raise ValueError("Schema drift detected: expected 'id' in platform response but received 'identifier_token'.")


@pytest.mark.asyncio
async def test_hard_case_5_schema_drift(monkeypatch):
    dest = DestinationModel(
        id="dest_drift_001",
        name="API Drifting Forum",
        url="https://drift.test",
        platform_key="discourse",
        surface="topic",
        connector_key="discourse",
        level="L3",
    )
    connection = ConnectionAuth()

    # Monkeypatch connector publish to simulate sudden third-party API drift
    from connectors.base import ConnectorRegistry
    mock_conn = ConnectorRegistry.get("discourse")
    async def failing_publish(*args, **kwargs):
        raise ValueError("Schema drift: Platform dropped required response field 'id'")
    monkeypatch.setattr(mock_conn, "publish", failing_publish)

    with pytest.raises(IncuBrixError) as exc_info:
        await DestinationCertifier.certify_destination(dest, connection)

    assert exc_info.value.code in (ErrorCode.SCHEMA_DRIFT_DETECTED, ErrorCode.PLATFORM_UNAVAILABLE)
    # Crucial gate requirement: failing destination must be immediately demoted to L0
    assert dest.level == "L0"
