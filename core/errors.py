"""Shared error types and envelope conforming to the IncuBrix contract."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ErrorCode(str, Enum):
    # IncuBrix Shared Error Codes
    DEST_SPEC_VIOLATION = "DEST_SPEC_VIOLATION"
    DEST_RULE_FREQUENCY_CAP = "DEST_RULE_FREQUENCY_CAP"
    CONNECTION_AUTH_EXPIRED = "CONNECTION_AUTH_EXPIRED"
    PLATFORM_RATE_LIMIT = "PLATFORM_RATE_LIMIT"
    PLATFORM_QUOTA_EXHAUSTED = "PLATFORM_QUOTA_EXHAUSTED"
    PLATFORM_CONTENT_REJECTED = "PLATFORM_CONTENT_REJECTED"
    PLATFORM_UNAVAILABLE = "PLATFORM_UNAVAILABLE"
    CONNECTOR_DISABLED = "CONNECTOR_DISABLED"

    # Integration / API Errors
    IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SCHEMA_DRIFT_DETECTED = "SCHEMA_DRIFT_DETECTED"
    UNAUTHORIZED = "UNAUTHORIZED"


# Error retryability mapping as specified in Appendix A
RETRYABLE_MAP = {
    ErrorCode.DEST_SPEC_VIOLATION: False,
    ErrorCode.DEST_RULE_FREQUENCY_CAP: True,  # Retryable later (after cap window)
    ErrorCode.CONNECTION_AUTH_EXPIRED: False,  # After reconnect
    ErrorCode.PLATFORM_RATE_LIMIT: True,  # Back off using platform reset time
    ErrorCode.PLATFORM_QUOTA_EXHAUSTED: True,  # Next window
    ErrorCode.PLATFORM_CONTENT_REJECTED: False,
    ErrorCode.PLATFORM_UNAVAILABLE: True,  # Retry with circuit breaker
    ErrorCode.CONNECTOR_DISABLED: False,
    ErrorCode.IDEMPOTENCY_KEY_REUSED: False,
    ErrorCode.INVALID_REQUEST: False,
    ErrorCode.NOT_FOUND: False,
    ErrorCode.INTERNAL_ERROR: True,
    ErrorCode.SCHEMA_DRIFT_DETECTED: False,
    ErrorCode.UNAUTHORIZED: False,
}


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool
    details: Optional[Dict[str, Any]] = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class IncuBrixError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: Optional[bool] = None,
        status_code: int = 400,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable if retryable is not None else RETRYABLE_MAP.get(code, False)
        self.status_code = status_code

    def to_envelope(self) -> ErrorEnvelope:
        return ErrorEnvelope(
            error=ErrorDetail(
                code=self.code.value,
                message=self.message,
                retryable=self.retryable,
                details=self.details,
            )
        )
