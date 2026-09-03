"""Turning an email template into a ready-to-send message.

Templates live in `app/templates/emails/` and are meant to be edited per
project. Each message is two files:

    emails/password_reset.html    HTML body; must declare `{% block subject %}`
    emails/password_reset.txt     plain-text alternative

**The subject lives inside the template**, in its own block. Wording is content,
and content belongs with the rest of the wording — otherwise rephrasing a
subject line means editing a service.

Adding a new email: copy both files, change the content, call
`render_email("your_name", to=..., **context)`.
"""

from __future__ import annotations

from typing import Any

from jinja2 import Template

from app.emails.base import EmailMessage
from app.templating import templates

# Autoescaping is right for the HTML body and wrong for the text one: it would
# turn every `&` in a URL into `&amp;`, which the recipient then pastes into a
# browser and finds broken. An overlay shares the loader and globals of the main
# environment, so email templates still see `settings` and the rest.
_text_env = templates.env.overlay(autoescape=False)


def render_email(name: str, *, to: str, **context: Any) -> EmailMessage:
    """Render `emails/<name>.html` and `emails/<name>.txt` into a message."""
    html_template = templates.env.get_template(f"emails/{name}.html")
    text_template = _text_env.get_template(f"emails/{name}.txt")

    return EmailMessage(
        to=to,
        subject=_render_subject(html_template, context),
        # Both stripped: the comment header every template carries would
        # otherwise ship as leading blank lines before the doctype.
        html=html_template.render(**context).strip(),
        text=text_template.render(**context).strip(),
    )


def _render_subject(template: Template, context: dict[str, Any]) -> str:
    """Render just the `subject` block of an email template.

    Jinja exposes each block of a template as a callable in `template.blocks`,
    which is what lets one file carry both the subject and the body. Only blocks
    declared in this very file are listed — an inherited one would not be — so
    every email template declares its own.
    """
    block = template.blocks.get("subject")
    if block is None:
        raise ValueError(f"{template.name} must declare a {{% block subject %}}")
    return "".join(block(template.new_context(context))).strip()
