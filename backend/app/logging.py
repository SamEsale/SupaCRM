from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    """Emit structured JSON logs for stdout/stderr collectors."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in (
            "request_id",
            "tenant_id",
            "actor_user_id",
            "user_id",
            "event_type",
            "severity",
            "scope",
            "ip_address",
            "email",
            "reason",
            "limit",
            "threshold",
            "attempt_count",
            "retry_after_seconds",
            "lockout_until",
            "method",
            "path",
            "query",
            "status_code",
            "duration_ms",
            "client_ip",
            "outcome",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Configure application logging for production-friendly structured stdout logs."""

    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())

    for logger_name in ("app", "uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.setLevel(level.upper())
        logger.propagate = True

    logging.captureWarnings(True)


logger = logging.getLogger("supacrm")
