"""Building the configured analytics sender(s).

Unlike email, GA4 and Meta are not mutually exclusive — a project can want
both, one, or neither active at the same time. `get_analytics_sender()` builds
a composite of whichever adapters have complete configuration; with none
configured, the composite is simply empty, which is the "off" state. No env
var chooses "console" the way `EMAIL_PROVIDER` does, because there is no
single provider to choose.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.analytics.base import AnalyticsEvent, AnalyticsSender
from app.analytics.providers.ga4 import Ga4AnalyticsSender
from app.analytics.providers.meta import MetaAnalyticsSender
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class CompositeAnalyticsSender:
    """Fans one event out to every configured destination.

    Each adapter already swallows its own delivery errors (see ADR-0011), so a
    failure in one destination never stops the others from receiving the
    event.
    """

    def __init__(self, senders: list[AnalyticsSender]) -> None:
        self._senders = senders

    def track(self, event: AnalyticsEvent) -> None:
        """Send the event to every configured destination."""
        for sender in self._senders:
            sender.track(event)


def _build_senders(settings: Settings) -> list[AnalyticsSender]:
    senders: list[AnalyticsSender] = []

    if settings.ga4_measurement_id and settings.ga4_api_secret:
        senders.append(
            Ga4AnalyticsSender(
                measurement_id=settings.ga4_measurement_id,
                api_secret=settings.ga4_api_secret,
            )
        )
    if settings.meta_pixel_id and settings.meta_capi_token:
        senders.append(
            MetaAnalyticsSender(
                pixel_id=settings.meta_pixel_id,
                access_token=settings.meta_capi_token,
            )
        )

    if not senders:
        logger.info("No analytics provider configured: events will not be sent anywhere.")

    return senders


@lru_cache(maxsize=1)
def get_analytics_sender() -> AnalyticsSender:
    """Return the process-wide analytics sender.

    Also a FastAPI dependency: inject `Analytics` from `app.deps` in a route,
    and a test can replace it through `app.dependency_overrides`.
    """
    return CompositeAnalyticsSender(_build_senders(get_settings()))
