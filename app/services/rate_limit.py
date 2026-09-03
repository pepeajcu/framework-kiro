"""Rate limiting.

Counting in PostgreSQL rather than in the process — see `app/models/rate_limit.py`
for why. The cost is one INSERT on a path that was already talking to the
database; what it buys is a limit that means the same thing with four workers as
with one, and that survives a deploy.

Every limit counts **two buckets at once**: the client IP and the account being
targeted. Either alone is easy to walk around — one IP per attempt defeats the
per-IP limit, one account per attempt defeats the per-account one.
"""

from __future__ import annotations

import datetime as dt
import secrets
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.rate_limit import RateLimitRepository

# Old rows are deleted on roughly one write in this many, instead of by a
# scheduled job the framework does not have. Cheap, self-healing, and it keeps
# the table from growing forever with buckets nobody will ever hit again.
PURGE_ODDS = 100

# How far back a purge keeps rows. Comfortably longer than any window here, so a
# purge can never delete a hit that still counts.
PURGE_AFTER = dt.timedelta(days=1)


@dataclass(frozen=True, slots=True)
class RateLimit:
    """How many attempts are allowed in how long."""

    max_attempts: int
    window: dt.timedelta


class RateLimiter:
    """Counts attempts and says when there have been too many."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.hits = RateLimitRepository(session)

    def is_blocked(self, buckets: Sequence[str], limit: RateLimit) -> bool:
        """Whether any of these buckets has already run out of attempts."""
        since = dt.datetime.now(tz=dt.UTC) - limit.window
        return any(self.hits.count_since(bucket, since) >= limit.max_attempts for bucket in buckets)

    def record(self, buckets: Sequence[str]) -> None:
        """Count one attempt against each bucket."""
        self.hits.record(buckets)

        if secrets.randbelow(PURGE_ODDS) == 0:
            self.hits.purge_older_than(dt.datetime.now(tz=dt.UTC) - PURGE_AFTER)

    def reset(self, buckets: Sequence[str]) -> None:
        """Forget the attempts in these buckets."""
        self.hits.clear(buckets)


def login_buckets(*, ip: str, email: str) -> list[str]:
    """The two buckets a login attempt counts against."""
    return [f"login:ip:{ip}", f"login:email:{email.strip().lower()}"[:128]]


def password_reset_buckets(*, ip: str, email: str) -> list[str]:
    """The two buckets a reset request counts against."""
    return [f"reset:ip:{ip}", f"reset:email:{email.strip().lower()}"[:128]]
