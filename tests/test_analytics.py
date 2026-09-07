"""Tests for server-side analytics: hashing, provider payloads, and dispatch."""

from __future__ import annotations

import httpx2
import pytest
from pydantic import ValidationError

from app.analytics.base import AnalyticsEvent
from app.analytics.dispatcher import CompositeAnalyticsSender, _build_senders
from app.analytics.hashing import sha256_lower
from app.analytics.providers.ga4 import Ga4AnalyticsSender
from app.analytics.providers.memory import MemoryAnalyticsSender
from app.analytics.providers.meta import MetaAnalyticsSender
from app.config import Environment, Settings

VALID_SETTINGS = {
    "secret_key": "x" * 32,
    "database_url": "postgresql+psycopg://user:pass@localhost:5432/db",
}


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None


class _Recorder:
    """Stands in for `httpx2.post`, keeping the last call's arguments."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return _FakeResponse()


# --- Hashing ------------------------------------------------------------


def test_sha256_lower_normalises_case_and_whitespace():
    assert sha256_lower(" Ana@Example.com ") == sha256_lower("ana@example.com")


def test_sha256_lower_is_a_real_sha256_digest():
    import hashlib

    assert sha256_lower("x") == hashlib.sha256(b"x").hexdigest()


# --- GA4 ------------------------------------------------------------------


def test_ga4_sender_posts_the_event_with_a_client_id(monkeypatch):
    recorder = _Recorder()
    monkeypatch.setattr(httpx2, "post", recorder)

    sender = Ga4AnalyticsSender(measurement_id="G-TEST", api_secret="secret")
    sender.track(AnalyticsEvent(name="sign_up", params={"client_id": "abc123"}))

    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call["params"] == {"measurement_id": "G-TEST", "api_secret": "secret"}
    assert call["json"]["client_id"] == "abc123"
    assert call["json"]["events"] == [{"name": "sign_up", "params": {}}]


def test_ga4_sender_invents_a_client_id_when_none_is_given(monkeypatch):
    recorder = _Recorder()
    monkeypatch.setattr(httpx2, "post", recorder)

    Ga4AnalyticsSender(measurement_id="G-TEST", api_secret="secret").track(
        AnalyticsEvent(name="login")
    )

    assert recorder.calls[0]["json"]["client_id"]


def test_ga4_sender_swallows_http_errors(monkeypatch):
    def fail(url, **kwargs):
        raise httpx2.HTTPError("boom")

    monkeypatch.setattr(httpx2, "post", fail)

    # Must not raise.
    Ga4AnalyticsSender(measurement_id="G-TEST", api_secret="secret").track(
        AnalyticsEvent(name="login")
    )


# --- Meta -------------------------------------------------------------------


def test_meta_sender_hashes_the_email_and_forwards_ip_and_user_agent(monkeypatch):
    recorder = _Recorder()
    monkeypatch.setattr(httpx2, "post", recorder)

    sender = MetaAnalyticsSender(pixel_id="123", access_token="tok")
    sender.track(
        AnalyticsEvent(
            name="sign_up",
            email="Ana@Example.com",
            ip_address="1.2.3.4",
            user_agent="pytest",
        )
    )

    payload = recorder.calls[0]["json"]["data"][0]
    assert payload["event_name"] == "sign_up"
    assert payload["user_data"]["em"] == sha256_lower("ana@example.com")
    assert payload["user_data"]["client_ip_address"] == "1.2.3.4"
    assert payload["user_data"]["client_user_agent"] == "pytest"
    assert "Ana@Example.com" not in str(recorder.calls[0]["json"])


def test_meta_sender_swallows_http_errors(monkeypatch):
    def fail(url, **kwargs):
        raise httpx2.HTTPError("boom")

    monkeypatch.setattr(httpx2, "post", fail)

    MetaAnalyticsSender(pixel_id="123", access_token="tok").track(AnalyticsEvent(name="login"))


# --- Composite / dispatch ----------------------------------------------------


def test_composite_sender_fans_out_to_every_sender():
    a, b = MemoryAnalyticsSender(), MemoryAnalyticsSender()
    composite = CompositeAnalyticsSender([a, b])

    event = AnalyticsEvent(name="sign_up")
    composite.track(event)

    assert a.sent == [event]
    assert b.sent == [event]


@pytest.mark.parametrize(
    ("overrides", "expected_count"),
    [
        ({}, 0),
        ({"ga4_measurement_id": "G-1", "ga4_api_secret": "s"}, 1),
        ({"meta_pixel_id": "1", "meta_capi_token": "t"}, 1),
        (
            {
                "ga4_measurement_id": "G-1",
                "ga4_api_secret": "s",
                "meta_pixel_id": "1",
                "meta_capi_token": "t",
            },
            2,
        ),
        ({"ga4_measurement_id": "G-1"}, 0),  # half a pair configures nothing locally
    ],
)
def test_build_senders_only_includes_fully_configured_providers(overrides, expected_count):
    settings = Settings(**VALID_SETTINGS, environment=Environment.LOCAL, **overrides)

    assert len(_build_senders(settings)) == expected_count


@pytest.mark.parametrize(
    "overrides",
    [
        {"ga4_measurement_id": "G-1", "ga4_api_secret": ""},
        {"meta_pixel_id": "1", "meta_capi_token": ""},
    ],
)
def test_a_half_configured_pair_fails_at_startup_in_production(overrides):
    with pytest.raises(ValidationError, match="together"):
        Settings(**VALID_SETTINGS, environment=Environment.PRODUCTION, **overrides)
