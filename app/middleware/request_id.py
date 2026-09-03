"""Giving every request an id.

The id ties together every log line a single request produces, which is the
difference between "there was a 500 at 14:03" and the six lines that explain it.
It is returned in `X-Request-ID` and printed on the 500 page, so a user can
quote it and you can find their exact request.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

# Read by the log formatter. A ContextVar rather than an argument threaded
# through every function: logging happens deep inside code that has no business
# knowing about HTTP.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# An incoming id is echoed back so a proxy or a client can correlate too — but
# it lands in the logs, so it is checked first. Anything else would let a caller
# write newlines and fake entries into the log.
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign or accept an id for each request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Bind the id for the duration of the request."""
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex

        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
