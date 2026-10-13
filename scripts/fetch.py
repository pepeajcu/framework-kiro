"""Download a file with a size cap, for the design commands.

Shared by `scripts/design.py` (fonts) and `scripts/motion.py` (vendored
libraries). The caller validates *what* it got; this only guarantees it did not
get more than it asked for, and turns network failures into messages.
"""

from __future__ import annotations

import httpx2

from app.design_engine.contract import DesignError

TIMEOUT = 20.0


def fetch_bytes(
    url: str,
    *,
    limit: int,
    label: str,
    client: httpx2.Client | None = None,
) -> bytes:
    """The body of `url`, refusing anything over `limit` bytes.

    `client` is injectable so tests can answer from a `MockTransport` instead of
    the network.
    """
    http = client or httpx2.Client(follow_redirects=True, timeout=TIMEOUT)
    data = bytearray()
    try:
        with http.stream("GET", url) as response:
            if response.status_code == 404:
                raise DesignError(f"{label}: no existe en el origen ({url})")
            response.raise_for_status()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > limit:
                    raise DesignError(f"{label}: pesa más de {limit // 1000} KB; lo descarto")
    except httpx2.HTTPError as exc:
        raise DesignError(f"no pude descargar {label}: {exc}") from exc
    finally:
        if client is None:
            http.close()
    return bytes(data)
