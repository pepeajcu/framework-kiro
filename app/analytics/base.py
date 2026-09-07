"""The contract between the application and wherever analytics events go.

Unlike email, an application can want more than one destination active at
once (GA4 and Meta both, say), so this is not a "pick one provider" seam —
see `app.analytics.dispatcher.CompositeAnalyticsSender`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AnalyticsEvent:
    """One thing that happened, generic enough for any destination to map.

    `email`, `ip_address` and `user_agent` are optional because not every
    event has a signed-in visitor behind it, and each provider uses whatever
    subset it needs — GA4 mainly wants `name`/`params`, Meta wants the hashed
    contact fields to match a person across devices.
    """

    name: str
    email: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    params: dict[str, str] = field(default_factory=dict)


class AnalyticsSender(Protocol):
    """What the application depends on. Providers satisfy it structurally.

    A Protocol, like `EmailSender` — an adapter never imports framework code,
    and a test double is any object with a matching `track`.
    """

    def track(self, event: AnalyticsEvent) -> None:
        """Record the event. Must never raise: see ADR-0011 for why."""
        ...
