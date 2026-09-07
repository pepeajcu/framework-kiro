"""Keeps events in a list instead of sending them. For tests.

Deliberately **not** selectable through configuration — see
`app.emails.providers.memory` for the same reasoning. Import it in a test and
override the `get_analytics_sender` dependency:

    sender = MemoryAnalyticsSender()
    app.dependency_overrides[get_analytics_sender] = lambda: sender
    ...
    assert sender.sent[0].name == "sign_up"
"""

from __future__ import annotations

from app.analytics.base import AnalyticsEvent


class MemoryAnalyticsSender:
    """`AnalyticsSender` that records events instead of delivering them."""

    def __init__(self) -> None:
        self.sent: list[AnalyticsEvent] = []

    def track(self, event: AnalyticsEvent) -> None:
        """Record the event."""
        self.sent.append(event)
