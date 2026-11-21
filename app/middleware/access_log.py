"""One structured log line per request.

Replaces uvicorn's own access log, which is emitted by the server outside the
application and therefore has no request id — leaving the id useless for exactly
the line you look at first. This one runs inside the request, so every field is
available and the JSON formatter can attach the id.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.access")

# Paths that would drown the log without telling you anything: every stylesheet
# on every page load, and a health probe every few seconds forever.
IGNORED_PREFIXES = ("/static", "/health")
_RESET_PATH_PREFIX = "/reset-password/"


def _redact_path(path: str) -> str:
    """Strip single-use bearer tokens from paths before they reach the access log."""
    if path.startswith(_RESET_PATH_PREFIX) and len(path) > len(_RESET_PATH_PREFIX):
        return f"{_RESET_PATH_PREFIX}[REDACTED]"
    return path


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log method, path, status and duration for every request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Time the request and log it once it has an outcome."""
        started = time.perf_counter()
        raw_path = request.url.path
        logged_path = _redact_path(raw_path)

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            if not raw_path.startswith(IGNORED_PREFIXES):
                logger.info(
                    "%s %s %s",
                    request.method,
                    logged_path,
                    500,
                    extra={
                        "method": request.method,
                        "path": logged_path,
                        "status": 500,
                        "duration_ms": duration_ms,
                    },
                )
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 1)

        if not raw_path.startswith(IGNORED_PREFIXES):
            logger.info(
                "%s %s %s",
                request.method,
                logged_path,
                response.status_code,
                # As `extra` rather than inside the message: a log aggregator can
                # filter on `status` or sort by `duration_ms` only if they are
                # fields, not words in a sentence.
                extra={
                    "method": request.method,
                    "path": logged_path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

        return response
