"""HTTP Endpoints exposing IncuBrix Connector Contract strictly as POST /connector/v1/{connector_key}/{method}."""

from typing import Optional
from fastapi import APIRouter, Header, Depends
from connectors.base import ConnectorRegistry
from core.contract import (
    ValidateRequest,
    ValidateResponse,
    PublishRequest,
    PublishResponse,
    GetStatusRequest,
    GetStatusResponse,
    DeleteRequest,
    DeleteResponse,
    FetchMetricsRequest,
    FetchMetricsResponse,
    RefreshAuthRequest,
    RefreshAuthResponse,
    BuildAssistPackRequest,
    BuildAssistPackResponse,
)
from core.errors import IncuBrixError, ErrorCode

router = APIRouter(prefix="/connector/v1", tags=["Connectors Contract"])


@router.post("/{connector_key}/validate", response_model=ValidateResponse)
async def validate_content(connector_key: str, req: ValidateRequest):
    """Validate rendition against destination and connection."""
    connector = ConnectorRegistry.get(connector_key)
    return await connector.validate(req.rendition, req.destination, req.connection)


@router.post("/{connector_key}/publish", response_model=PublishResponse)
async def publish_content(
    connector_key: str,
    req: PublishRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Publish rendition to destination."""
    effective_key = idempotency_key or req.idempotency_key
    if not effective_key:
        raise IncuBrixError(
            code=ErrorCode.INVALID_REQUEST,
            message="Idempotency key must be provided either in header 'Idempotency-Key' or request body.",
            status_code=400,
        )
    connector = ConnectorRegistry.get(connector_key)
    return await connector.publish(req.rendition, req.destination, req.connection, effective_key)


@router.post("/{connector_key}/get_status", response_model=GetStatusResponse)
async def get_post_status(connector_key: str, req: GetStatusRequest):
    """Get status of an existing publication."""
    connector = ConnectorRegistry.get(connector_key)
    return await connector.get_status(req.platform_post_id, req.connection)


@router.post("/{connector_key}/delete", response_model=DeleteResponse)
async def delete_post(connector_key: str, req: DeleteRequest):
    """Delete a post from the destination."""
    connector = ConnectorRegistry.get(connector_key)
    return await connector.delete(req.platform_post_id, req.connection)


@router.post("/{connector_key}/fetch_metrics", response_model=FetchMetricsResponse)
async def fetch_metrics(connector_key: str, req: FetchMetricsRequest):
    """Fetch post performance metrics."""
    connector = ConnectorRegistry.get(connector_key)
    return await connector.fetch_metrics(req.platform_post_id, req.connection, req.since)


@router.post("/{connector_key}/refresh_auth", response_model=RefreshAuthResponse)
async def refresh_auth(connector_key: str, req: RefreshAuthRequest):
    """Refresh platform authentication tokens."""
    connector = ConnectorRegistry.get(connector_key)
    return await connector.refresh_auth(req.connection)


@router.post("/{connector_key}/build_assist_pack", response_model=BuildAssistPackResponse)
async def build_assist_pack(connector_key: str, req: BuildAssistPackRequest):
    """Build assistance package for human posting (assisted tier)."""
    connector = ConnectorRegistry.get(connector_key)
    return await connector.build_assist_pack(req.rendition, req.destination)
