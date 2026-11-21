"""Structured JSON logging with correlation IDs and secret redaction."""

import re
import sys
import logging
from typing import Any, MutableMapping
import structlog

# Patterns to automatically redact
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|authorization|private[_-]?key)[\"']?\s*[:=]\s*[\"']?([^\"'\s,]+)[\"']?"),
    re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]+)", re.IGNORECASE),
]

SENSITIVE_KEYS = {
    "api_key",
    "secret",
    "token",
    "password",
    "authorization",
    "secret_key",
    "access_token",
    "id_token",
    "refresh_token",
    "client_secret",
}


def redact_value(val: Any) -> Any:
    if isinstance(val, str):
        redacted = val
        for pat in SECRET_PATTERNS:
            redacted = pat.sub(r"\1=[REDACTED]", redacted)
        return redacted
    elif isinstance(val, dict):
        return {k: ("[REDACTED]" if k.lower() in SENSITIVE_KEYS else redact_value(v)) for k, v in val.items()}
    elif isinstance(val, list):
        return [redact_value(item) for item in val]
    return val


def secret_redaction_filter(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Structlog processor that traverses event_dict and redacts secrets."""
    for key, val in list(event_dict.items()):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
        else:
            event_dict[key] = redact_value(val)
    return event_dict


def setup_logging(log_level: str = "INFO") -> None:
    """Configures structured JSON logging."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            secret_redaction_filter,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "incubrix") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
