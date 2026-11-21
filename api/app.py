"""FastAPI Application factory for IncuBrix Distribution Connector Service."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from core.logging import setup_logging
from core.config import settings
from core.errors import ErrorEnvelope, ErrorDetail, ErrorCode
from api.middleware import CorrelationIdMiddleware
from api.v1.health_routes import router as health_router

setup_logging(settings.LOG_LEVEL)

app = FastAPI(
    title="IncuBrix Distribution Connector Service",
    description="Long-Tail Destination Network connector service and publishing intelligence engine.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Middleware
app.add_middleware(CorrelationIdMiddleware)


# Validation Error Handler matching IncuBrix format
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code=ErrorCode.INVALID_REQUEST.value,
            message="Request validation failed",
            retryable=False,
            details={"errors": exc.errors()},
        )
    )
    return JSONResponse(status_code=422, content=envelope.model_dump())


# Include Routers
app.include_router(health_router, prefix="")
app.include_router(health_router, prefix="/api/v1")

import connectors
from api.v1.connector_routes import router as connector_router
from api.v1.destinations import router as destinations_router
from api.v1.job_routes import router as job_router

app.include_router(connector_router)
app.include_router(destinations_router)
app.include_router(job_router)
