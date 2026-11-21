"""Base class and registry for IncuBrix connectors."""

from abc import ABC, abstractmethod
from typing import Dict, Type, Optional, List
import yaml
from core.contract import (
    ConnectorManifest,
    ContentRendition,
    DestinationConfig,
    ConnectionAuth,
    ValidateResponse,
    ViolationItem,
    PublishResponse,
    GetStatusResponse,
    DeleteResponse,
    FetchMetricsResponse,
    RefreshAuthResponse,
    BuildAssistPackResponse,
)
from core.errors import IncuBrixError, ErrorCode
from core.config import settings


class BaseConnector(ABC):
    """Abstract Base Connector implementing IncuBrix Appendix A Contract."""

    def __init__(self, manifest: ConnectorManifest):
        self.manifest = manifest

    @property
    def key(self) -> str:
        return self.manifest.key

    def check_enabled(self) -> None:
        disabled_keys = [k.strip() for k in settings.DISABLED_CONNECTORS.split(",") if k.strip()]
        if self.key in disabled_keys:
            raise IncuBrixError(
                code=ErrorCode.CONNECTOR_DISABLED,
                message=f"Connector '{self.key}' is currently disabled by operator kill-switch.",
                status_code=403,
            )

    def validate_spec(
        self,
        rendition: ContentRendition,
        destination: DestinationConfig,
    ) -> List[ViolationItem]:
        """Validates surface spec constraints (length, media types, links)."""
        violations: List[ViolationItem] = []
        surface_def = next(
            (s for s in self.manifest.surfaces if s.key == destination.surface),
            self.manifest.surfaces[0] if self.manifest.surfaces else None
        )
        if not surface_def:
            violations.append(
                ViolationItem(
                    field="surface",
                    message=f"Surface '{destination.surface}' is not supported by connector {self.key}",
                    rule="surface_support",
                )
            )
            return violations

        spec = destination.spec_overrides or surface_def.spec

        # Title check
        if spec.title_max_chars is not None:
            if rendition.title and len(rendition.title) > spec.title_max_chars:
                violations.append(
                    ViolationItem(
                        field="title",
                        message=f"Title length ({len(rendition.title)}) exceeds maximum of {spec.title_max_chars} chars",
                        rule="title_max_chars",
                    )
                )

        # Body check
        if spec.body_max_chars is not None:
            if len(rendition.body) > spec.body_max_chars:
                violations.append(
                    ViolationItem(
                        field="body",
                        message=f"Body length ({len(rendition.body)}) exceeds maximum of {spec.body_max_chars} chars",
                        rule="body_max_chars",
                    )
                )

        # Links allowed check
        if spec.links_allowed is False:
            if "http://" in rendition.body or "https://" in rendition.body:
                violations.append(
                    ViolationItem(
                        field="body",
                        message="Links are not allowed in this destination surface",
                        rule="links_allowed",
                    )
                )

        # Media checks
        if rendition.media:
            allowed_types = spec.media_types_allowed or []
            for idx, media_item in enumerate(rendition.media):
                if media_item.type not in allowed_types:
                    violations.append(
                        ViolationItem(
                            field=f"media[{idx}].type",
                            message=f"Media type '{media_item.type}' is not supported by surface '{surface_def.key}'",
                            rule="media_types_allowed",
                        )
                    )
            if spec.max_media_count is not None and len(rendition.media) > spec.max_media_count:
                violations.append(
                    ViolationItem(
                        field="media",
                        message=f"Media item count ({len(rendition.media)}) exceeds maximum of {spec.max_media_count}",
                        rule="max_media_count",
                    )
                )

        return violations

    async def validate(
        self,
        rendition: ContentRendition,
        destination: DestinationConfig,
        connection: Optional[ConnectionAuth] = None,
    ) -> ValidateResponse:
        self.check_enabled()
        violations = self.validate_spec(rendition, destination)
        return ValidateResponse(ok=len(violations) == 0, violations=violations)

    @abstractmethod
    async def publish(
        self,
        rendition: ContentRendition,
        destination: DestinationConfig,
        connection: ConnectionAuth,
        idempotency_key: str,
    ) -> PublishResponse:
        pass

    @abstractmethod
    async def get_status(
        self,
        platform_post_id: str,
        connection: ConnectionAuth,
    ) -> GetStatusResponse:
        pass

    @abstractmethod
    async def delete(
        self,
        platform_post_id: str,
        connection: ConnectionAuth,
    ) -> DeleteResponse:
        pass

    async def fetch_metrics(
        self,
        platform_post_id: str,
        connection: ConnectionAuth,
        since: Optional[str] = None,
    ) -> FetchMetricsResponse:
        raise IncuBrixError(
            code=ErrorCode.INVALID_REQUEST,
            message=f"fetch_metrics is not implemented or supported for connector {self.key}",
            status_code=501,
        )

    async def refresh_auth(
        self,
        connection: ConnectionAuth,
    ) -> RefreshAuthResponse:
        raise IncuBrixError(
            code=ErrorCode.INVALID_REQUEST,
            message=f"refresh_auth is not implemented or supported for connector {self.key}",
            status_code=501,
        )

    async def build_assist_pack(
        self,
        rendition: ContentRendition,
        destination: DestinationConfig,
    ) -> BuildAssistPackResponse:
        raise IncuBrixError(
            code=ErrorCode.INVALID_REQUEST,
            message=f"build_assist_pack is only available on assisted tier connectors, not {self.key}",
            status_code=400,
        )


class ConnectorRegistry:
    """Registry holding all active connector instances."""

    _connectors: Dict[str, BaseConnector] = {}

    @classmethod
    def register(cls, connector: BaseConnector) -> None:
        cls._connectors[connector.key] = connector

    @classmethod
    def get(cls, key: str) -> BaseConnector:
        if key not in cls._connectors:
            raise IncuBrixError(
                code=ErrorCode.NOT_FOUND,
                message=f"Connector '{key}' not found in registry.",
                status_code=404,
            )
        connector = cls._connectors[key]
        connector.check_enabled()
        return connector

    @classmethod
    def all_connectors(cls) -> Dict[str, BaseConnector]:
        return cls._connectors
