"""Logging setup.

Two formats, one per audience. In a deployed environment logs are JSON, one
object per line, because that is what a log aggregator can filter by
`request_id` or `level`. On a laptop they are a readable line, because nobody
greps their own terminal.

Called once from `app.main.create_app`. Never configure logging anywhere else:
two handlers on the root logger means every line printed twice.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import sys
from typing import Any

from app.config import Settings
from app.middleware.request_id import request_id_var

# Attributes every LogRecord carries. Anything else was passed by the caller as
# `extra=` and belongs in the output.
_STANDARD_FIELDS = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()
    | {"message", "asctime", "taskName"}
)


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with the request id attached."""

    def format(self, record: logging.LogRecord) -> str:
        """Render the record."""
        payload: dict[str, Any] = {
            "time": dt.datetime.fromtimestamp(record.created, tz=dt.UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }

        # Whatever the caller passed as `extra={...}` travels too, so a log line
        # can carry the user id or the order number that explains it.
        payload.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD_FIELDS})

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # `default=str` so a UUID or a datetime in `extra=` never turns a log
        # line into a TypeError inside the logger.
        return json.dumps(payload, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """A readable line for local development, request id included."""

    def format(self, record: logging.LogRecord) -> str:
        """Render the record."""
        request_id = request_id_var.get()[:8]
        base = f"{record.levelname:<8} {request_id} {record.name}: {record.getMessage()}"
        if record.exc_info:
            return f"{base}\n{self.formatException(record.exc_info)}"
        return base


# Our handler is named so that a second call to `configure_logging` can replace
# exactly the one it installed last time.
HANDLER_NAME = "kiro"


def configure_logging(settings: Settings) -> None:
    """Install the formatter every logger in the process will use.

    Only ever touches its own handler. The tempting one-liner —
    `root.handlers = [handler]` — also throws away pytest's `caplog` handler,
    which is installed before fixtures run: every project's logging assertions
    would then quietly capture nothing. Being called twice (a test that builds
    two apps) must not double every line either, hence the named handler.
    """
    root = logging.getLogger()
    for installed in [h for h in root.handlers if h.get_name() == HANDLER_NAME]:
        root.removeHandler(installed)

    handler = logging.StreamHandler(sys.stdout)
    handler.set_name(HANDLER_NAME)
    handler.setFormatter(JsonFormatter() if settings.is_production else ConsoleFormatter())

    root.addHandler(handler)
    root.setLevel(settings.log_level)

    # uvicorn installs its own handlers on import. Left alone, every line would
    # appear twice: once in its format and once in ours.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True

    # uvicorn's access log is emitted by the server, outside the application, so
    # it has no request id. `AccessLogMiddleware` writes a better line from
    # inside the request; silencing this one keeps them from appearing twice.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
