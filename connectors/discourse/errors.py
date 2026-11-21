"""Error mapping helpers for Discourse platform."""

import httpx
from core.errors import IncuBrixError, ErrorCode


def map_discourse_error(exc: Exception) -> IncuBrixError:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 429:
            retry_after = exc.response.headers.get("Retry-After", "60")
            reset_seconds = int(retry_after) if retry_after.isdigit() else 60
            return IncuBrixError(
                code=ErrorCode.PLATFORM_RATE_LIMIT,
                message=f"Discourse rate limit hit. Backing off for {reset_seconds}s.",
                details={"reset_seconds": reset_seconds, "retry_after": retry_after},
                retryable=True,
                status_code=429,
            )
        elif status in (401, 403):
            return IncuBrixError(
                code=ErrorCode.CONNECTION_AUTH_EXPIRED,
                message="Discourse API Key or username is invalid or revoked.",
                details={"status_code": status, "response": exc.response.text},
                retryable=False,
                status_code=401,
            )
        elif status == 422:
            return IncuBrixError(
                code=ErrorCode.PLATFORM_CONTENT_REJECTED,
                message=f"Discourse rejected content: {exc.response.text}",
                details={"status_code": 422, "response": exc.response.text},
                retryable=False,
                status_code=422,
            )
        elif status >= 500:
            return IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Discourse server error ({status})",
                details={"status_code": status},
                retryable=True,
                status_code=502,
            )
    elif isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return IncuBrixError(
            code=ErrorCode.PLATFORM_UNAVAILABLE,
            message="Discourse connection timed out or failed to reach host.",
            details={"error": str(exc)},
            retryable=True,
            status_code=504,
        )
    return IncuBrixError(
        code=ErrorCode.INTERNAL_ERROR,
        message=f"Unexpected error communicating with Discourse: {str(exc)}",
        status_code=500,
    )
