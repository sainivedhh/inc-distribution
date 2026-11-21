"""Middleware for correlation IDs, structured logging, and error handling."""

import uuid
import time
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from core.errors import IncuBrixError, ErrorEnvelope, ErrorDetail, ErrorCode
from core.config import settings

logger = structlog.get_logger("api.middleware")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        corr_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=corr_id,
            path=request.url.path,
            method=request.method,
        )

        start_time = time.time()
        try:
            response = await call_next(request)
            response.headers["X-Correlation-Id"] = corr_id
            elapsed = time.time() - start_time
            logger.info("request_completed", status_code=response.status_code, elapsed_s=elapsed)
            return response
        except IncuBrixError as exc:
            elapsed = time.time() - start_time
            logger.warning("incubrix_error", code=exc.code.value, message=exc.message, elapsed_s=elapsed)
            envelope = exc.to_envelope()
            resp = JSONResponse(
                status_code=exc.status_code,
                content=envelope.model_dump(),
            )
            resp.headers["X-Correlation-Id"] = corr_id
            return resp
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("unhandled_error", error=str(exc), elapsed_s=elapsed)
            envelope = ErrorEnvelope(
                error=ErrorDetail(
                    code=ErrorCode.INTERNAL_ERROR.value,
                    message="Internal server error",
                    retryable=True,
                    details={"error": str(exc)} if settings.DEBUG else {},
                )
            )
            resp = JSONResponse(
                status_code=500,
                content=envelope.model_dump(),
            )
            resp.headers["X-Correlation-Id"] = corr_id
            return resp
