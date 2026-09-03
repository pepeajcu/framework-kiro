"""Data access for rate limiting."""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

from sqlalchemy import delete, func, select

from app.models.rate_limit import RateLimitHit
from app.repositories.base import BaseRepository


class RateLimitRepository(BaseRepository[RateLimitHit]):
    """Counted attempts, grouped into buckets."""

    model = RateLimitHit

    def count_since(self, bucket: str, since: dt.datetime) -> int:
        """How many hits this bucket has taken since a moment."""
        stmt = select(func.count()).where(
            RateLimitHit.bucket == bucket,
            RateLimitHit.created_at >= since,
        )
        return self.session.scalar(stmt) or 0

    def record(self, buckets: Sequence[str]) -> None:
        """Record one hit in each bucket."""
        self.session.add_all([RateLimitHit(bucket=bucket) for bucket in buckets])
        self.session.flush()

    def clear(self, buckets: Sequence[str]) -> None:
        """Forget every hit in these buckets.

        Called after a successful login: the attempts that led up to it were
        somebody remembering their own password, not an attack.
        """
        self.session.execute(delete(RateLimitHit).where(RateLimitHit.bucket.in_(buckets)))
        self.session.flush()

    def purge_older_than(self, cutoff: dt.datetime) -> None:
        """Delete hits that no window can still care about."""
        self.session.execute(delete(RateLimitHit).where(RateLimitHit.created_at < cutoff))
        self.session.flush()
