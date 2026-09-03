"""Recorded attempts, for rate limiting."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class RateLimitHit(UUIDPrimaryKeyMixin, Base):
    """One recorded attempt at something worth limiting.

    In PostgreSQL rather than in memory, deliberately. A dictionary in the
    process is free, but it empties on every deploy and each uvicorn worker
    keeps its own — with four workers a limit of 10 is really a limit of 40, and
    nobody notices until someone counts. The table is small, the write is one
    INSERT on a path that already talks to the database, and it is correct
    across restarts and workers alike.

    No `updated_at`: a hit is an event, not a record that changes.
    """

    __tablename__ = "rate_limit_hits"

    # What is being limited: "login:ip:1.2.3.4", "login:email:ana@example.com".
    # The bucket carries its own scope so one table serves every limit.
    bucket: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Every query is "how many hits in this bucket since this moment", which is
    # exactly what a composite index answers without touching the table.
    __table_args__ = (Index("ix_rate_limit_hits_bucket_created_at", "bucket", "created_at"),)
