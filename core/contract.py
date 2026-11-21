"""Contract schemas and types strictly matching IncuBrix Appendix A."""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Manifest Models
# -------------------------------------------------------------

class SurfaceSpec(BaseModel):
    title_max_chars: Optional[int] = None
    body_max_chars: Optional[int] = None
    links_allowed: bool = True
    media_types_allowed: Optional[List[str]] = Field(default_factory=lambda: ["image", "video_link"])
    max_media_count: Optional[int] = 10
    requires_flair: Optional[bool] = False


class SurfaceDefinition(BaseModel):
    key: str
    content_types: List[str]
    spec: SurfaceSpec


class RateLimits(BaseModel):
    per_connection: Dict[str, int] = Field(
        default_factory=lambda: {"requests": 60, "per_seconds": 60}
    )


class ConnectorManifest(BaseModel):
    key: str
    version: str = "1.0.0"
    tier: Literal["native", "protocol", "bridge", "feed", "assisted"]
    auth: Literal["oauth2", "api_key", "bot_token", "none", "hmac"]
    surfaces: List[SurfaceDefinition]
    rate_limits: RateLimits
    capabilities: List[Literal["publish", "status", "delete", "metrics", "refresh_auth", "assist_pack"]]
    error_map: Dict[str, str]
    instance_param: Optional[str] = None


# -------------------------------------------------------------
# Rendition, Destination & Connection Payload Models
# -------------------------------------------------------------

class MediaItem(BaseModel):
    type: Literal["image", "video", "audio", "document"]
    url: str
    alt_text: Optional[str] = None
    thumbnail_url: Optional[str] = None


class ContentRendition(BaseModel):
    title: Optional[str] = None
    body: str
    media: Optional[List[MediaItem]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    ai_generated: bool = False
    ai_disclosure_text: Optional[str] = None
    language: str = "en"


class DestinationConfig(BaseModel):
    destination_id: Optional[str] = None
    name: str
    url: str
    platform_key: str
    surface: str
    category: Optional[str] = None
    audience_tags: Optional[List[str]] = Field(default_factory=list)
    language: str = "en"
    geo: Optional[str] = "global"
    est_audience: Optional[int] = 0
    rules_url: Optional[str] = None
    frequency_cap: Optional[str] = "1 per 7 days"
    self_promo_allowed: bool = True
    link_policy: Optional[str] = "allowed"  # allowed | no_links | max_links | domains
    disclosure_required: bool = False
    automation_allowed: bool = True
    connector_key: str
    relevance_score: Optional[int] = 3
    relevance_reason: Optional[str] = None
    level: Optional[str] = "L0"
    last_certified_at: Optional[str] = None
    spec_overrides: Optional[SurfaceSpec] = None


class ConnectionAuth(BaseModel):
    connection_id: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    secret: Optional[str] = None
    jwt_token: Optional[str] = None
    base_url: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = Field(default_factory=dict)


# -------------------------------------------------------------
# Appendix A Request & Response Method Models
# -------------------------------------------------------------

class ValidateRequest(BaseModel):
    rendition: ContentRendition
    destination: DestinationConfig
    connection: Optional[ConnectionAuth] = None


class ViolationItem(BaseModel):
    field: str
    message: str
    rule: str
    severity: Literal["error", "warning"] = "error"


class ValidateResponse(BaseModel):
    ok: bool
    violations: List[ViolationItem] = Field(default_factory=list)


class PublishRequest(BaseModel):
    rendition: ContentRendition
    destination: DestinationConfig
    connection: ConnectionAuth
    idempotency_key: str


class PublishResponse(BaseModel):
    platform_post_id: str
    live_url: str
    status: Literal["published", "pending", "scheduled", "draft"] = "published"


class GetStatusRequest(BaseModel):
    platform_post_id: str
    connection: ConnectionAuth


class GetStatusResponse(BaseModel):
    status: Literal["published", "deleted", "archived", "flagged", "not_found"]
    live_url: Optional[str] = None


class DeleteRequest(BaseModel):
    platform_post_id: str
    connection: ConnectionAuth


class DeleteResponse(BaseModel):
    deleted: bool


class FetchMetricsRequest(BaseModel):
    platform_post_id: str
    connection: ConnectionAuth
    since: Optional[str] = None


class FetchMetricsResponse(BaseModel):
    views: Optional[int] = 0
    likes: Optional[int] = 0
    comments: Optional[int] = 0
    shares: Optional[int] = 0
    saves: Optional[int] = 0
    watch_time_s: Optional[int] = 0
    clicks: Optional[int] = 0


class RefreshAuthRequest(BaseModel):
    connection: ConnectionAuth


class RefreshAuthResponse(BaseModel):
    expires_at: str
    access_token: Optional[str] = None


class ChecklistItem(BaseModel):
    rule: str
    checked: bool = False
    instruction: str


class BuildAssistPackRequest(BaseModel):
    rendition: ContentRendition
    destination: DestinationConfig


class BuildAssistPackResponse(BaseModel):
    files: List[str] = Field(default_factory=list)
    caption: str
    deep_link: str
    checklist: List[ChecklistItem] = Field(default_factory=list)
