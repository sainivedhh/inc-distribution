"""Ghost Native Connector (Admin API)."""

from pathlib import Path
import yaml
import time
import jwt
import httpx
from core.contract import (
    ConnectorManifest,
    ContentRendition,
    DestinationConfig,
    ConnectionAuth,
    PublishResponse,
    GetStatusResponse,
    DeleteResponse,
)
from core.errors import IncuBrixError, ErrorCode
from connectors.base import BaseConnector
from core.config import settings


class GhostConnector(BaseConnector):
    def __init__(self):
        manifest_path = Path(__file__).parent / "manifest.yaml"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        super().__init__(ConnectorManifest(**data))

    def _generate_ghost_jwt(self, api_key: str) -> str:
        """Ghost Admin API keys are id:secret format (secret is hex)."""
        if not api_key or ":" not in api_key:
            return "mock-Ghost-token"
        key_id, secret = api_key.split(":")
        try:
            iat = int(time.time())
            header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
            payload = {"iat": iat, "exp": iat + 5 * 60, "aud": "/admin/"}
            token = jwt.encode(payload, bytes.fromhex(secret), algorithm="HS256", headers=header)
            return token
        except Exception:
            return "mock-Ghost-token"

    async def publish(
        self,
        rendition: ContentRendition,
        destination: DestinationConfig,
        connection: ConnectionAuth,
        idempotency_key: str,
    ) -> PublishResponse:
        self.check_enabled()
        violations = self.validate_spec(rendition, destination)
        if violations:
            raise IncuBrixError(
                code=ErrorCode.DEST_SPEC_VIOLATION,
                message="Ghost post violates surface specifications",
                details={"violations": [v.model_dump() for v in violations]},
                status_code=400,
            )

        base_url = connection.base_url or destination.url.rstrip("/")
        if settings.SIMULATION_MODE:
            return PublishResponse(
                platform_post_id=f"ghost_{idempotency_key[:8]}",
                live_url=f"https://ghost.incubrix.test/post/{idempotency_key[:8]}",
                status="published",
            )

        token = self._generate_ghost_jwt(connection.api_key or "mock_id:abcdef1234567890abcdef1234567890")
        endpoint = f"{base_url}/ghost/api/admin/posts/"
        headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}
        payload = {
            "posts": [
                {
                    "title": rendition.title or "Untitled Ghost Post",
                    "html": f"<p>{rendition.body}</p>",
                    "status": "published",
                    "canonical_url": rendition.canonical_url,
                }
            ]
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(endpoint, headers=headers, json=payload)
                if res.status_code == 401:
                    raise IncuBrixError(code=ErrorCode.CONNECTION_AUTH_EXPIRED, message="Ghost token expired/invalid", status_code=401)
                res.raise_for_status()
                data = res.json()
                post = data["posts"][0]
                return PublishResponse(
                    platform_post_id=str(post["id"]),
                    live_url=post.get("url", f"{base_url}/{post['slug']}/"),
                    status="published",
                )
            except IncuBrixError:
                raise
            except Exception as e:
                raise IncuBrixError(code=ErrorCode.PLATFORM_UNAVAILABLE, message=f"Ghost API error: {str(e)}", retryable=True, status_code=502)

    async def get_status(self, platform_post_id: str, connection: ConnectionAuth) -> GetStatusResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/ghost"
        if settings.SIMULATION_MODE:
            return GetStatusResponse(status="published", live_url=f"https://ghost.incubrix.test/post/{platform_post_id}")
        token = self._generate_ghost_jwt(connection.api_key or "mock_id:abcdef")
        endpoint = f"{base_url}/ghost/api/admin/posts/{platform_post_id}/"
        headers = {"Authorization": f"Ghost {token}"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(endpoint, headers=headers)
            if res.status_code == 404:
                return GetStatusResponse(status="not_found")
            res.raise_for_status()
            data = res.json()
            post = data["posts"][0]
            return GetStatusResponse(
                status="published" if post.get("status") == "published" else "draft",
                live_url=post.get("url"),
            )

    async def delete(self, platform_post_id: str, connection: ConnectionAuth) -> DeleteResponse:
        self.check_enabled()
        base_url = connection.base_url or "http://localhost:8080/ghost"
        if settings.SIMULATION_MODE:
            return DeleteResponse(deleted=True)
        token = self._generate_ghost_jwt(connection.api_key or "mock_id:abcdef")
        endpoint = f"{base_url}/ghost/api/admin/posts/{platform_post_id}/"
        headers = {"Authorization": f"Ghost {token}"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.delete(endpoint, headers=headers)
            return DeleteResponse(deleted=res.status_code in (200, 204, 404))
