"""Server-side analytics events.

    from app.analytics import AnalyticsEvent
    from app.deps import Analytics

    def on_signup(analytics: Analytics, background_tasks: BackgroundTasks, user: User) -> None:
        background_tasks.add_task(
            analytics.track, AnalyticsEvent(name="sign_up", email=user.email)
        )

Fired from `BackgroundTasks`, after the response is otherwise ready: a visitor
must never wait on Google or Meta to finish logging in. Which destinations
actually receive the event is decided by which of GA4/Meta have complete
configuration — see `dispatcher.py`.
"""

from app.analytics.base import AnalyticsEvent, AnalyticsSender
from app.analytics.dispatcher import get_analytics_sender
from app.analytics.providers.memory import MemoryAnalyticsSender

__all__ = [
    "AnalyticsEvent",
    "AnalyticsSender",
    "MemoryAnalyticsSender",
    "get_analytics_sender",
]
