"""Tests for the transactional email layer.

What is worth pinning down here is the seam, not the network: that a template
produces a subject and two bodies, that the plain-text one is not HTML-escaped,
and that a provider which cannot send fails at boot instead of at send time.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.emails import MemoryEmailSender, render_email
from app.emails.providers.console import ConsoleEmailSender
from app.emails.render import _render_subject
from app.templating import templates

RESET_URL = "https://example.com/reset-password/tok?next=/panel&ref=mail"

VALID_SETTINGS = {
    "secret_key": "x" * 32,
    "database_url": "postgresql+psycopg://user:pass@localhost:5432/db",
}


def render_reset():
    return render_email(
        "password_reset",
        to="alguien@example.com",
        reset_url=RESET_URL,
        expires_in_minutes=30,
    )


def test_subject_comes_from_the_template_block():
    """The subject is content: it lives in the template, not in Python."""
    message = render_reset()

    assert "contraseña" in message.subject.lower()
    assert "\n" not in message.subject


def test_both_bodies_are_rendered():
    message = render_reset()

    assert message.html.startswith("<!doctype html>")
    assert RESET_URL in message.text
    assert "{{" not in message.html


def test_text_body_does_not_escape_ampersands():
    """Regression guard for the autoescape overlay in `app.emails.render`.

    With the shared HTML environment, `?next=/panel&ref=mail` would reach the
    recipient as `&amp;ref=mail` — a link that looks fine and 404s when pasted.
    """
    message = render_reset()

    assert "&ref=mail" in message.text
    assert "&amp;" not in message.text
    # The HTML body must still escape it: there the entity is the correct form.
    assert "&amp;ref=mail" in message.html


def test_missing_subject_block_is_reported_clearly():
    """A template without a subject block fails with a message that names it."""
    template = templates.env.from_string("<p>sin asunto</p>")

    with pytest.raises(ValueError, match="subject"):
        _render_subject(template, {})


def test_memory_sender_records_instead_of_sending():
    sender = MemoryEmailSender()
    sender.send(render_reset())

    assert len(sender.outbox) == 1
    assert sender.last.to == "alguien@example.com"

    sender.clear()
    with pytest.raises(AssertionError, match="no email was sent"):
        _ = sender.last


def test_console_sender_prints_the_text_body(capsys):
    ConsoleEmailSender().send(render_reset())

    printed = capsys.readouterr().out
    assert "alguien@example.com" in printed
    assert RESET_URL in printed


def test_from_header_uses_the_name_when_there_is_one():
    named = Settings(**VALID_SETTINGS, email_from="no-reply@x.test", email_from_name="Tienda")
    bare = Settings(**VALID_SETTINGS, email_from="no-reply@x.test", email_from_name="")

    assert named.email_from_header == "Tienda <no-reply@x.test>"
    assert bare.email_from_header == "no-reply@x.test"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"email_provider": "resend", "resend_api_key": ""}, "RESEND_API_KEY"),
        ({"email_provider": "smtp", "smtp_host": ""}, "SMTP_HOST"),
    ],
)
def test_unusable_email_provider_fails_at_startup(overrides, expected):
    """Better a container that refuses to boot than a password reset that vanishes."""
    with pytest.raises(ValidationError, match=expected):
        Settings(**VALID_SETTINGS, **overrides)
