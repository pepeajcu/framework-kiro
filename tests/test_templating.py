"""The template environment: what gets escaped, and what must not be.

Starlette's default only escapes `.html`, `.htm` and `.xml`. The component macros
are `*.html.jinja`, and they print what a visitor typed (a form field's value, a
toast's title), so a `.jinja` file that is not escaped is an XSS waiting for the
next macro that echoes input.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.emails import render_email
from app.templating import TEMPLATES_DIR, templates

HOSTILE = '"><script>alert(1)</script>'


def _template_names() -> list[str]:
    return sorted(
        path.relative_to(TEMPLATES_DIR).as_posix()
        for path in TEMPLATES_DIR.rglob("*")
        if path.is_file()
    )


@pytest.mark.parametrize("name", _template_names())
def test_every_markup_template_is_escaped_and_plain_text_is_not(name):
    """A new extension that slips past the list would be rendered raw."""
    suffix = Path(name).suffix

    if suffix == ".txt":
        assert not templates.env.autoescape(name)
    else:
        assert suffix in {".html", ".jinja"}, f"extensión nueva sin decidir: {name}"
        assert templates.env.autoescape(name), name


def test_a_form_field_escapes_its_value_label_and_error():
    macro = templates.env.from_string(
        '{% from "components/form.html.jinja" import field %}'
        "{{ field('email', label, value=value, errors={'email': error}, help=help) }}"
    )

    html = macro.render(label=HOSTILE, value=HOSTILE, error=HOSTILE, help=HOSTILE)

    assert "<script>" not in html
    assert html.count("&lt;script&gt;") >= 4


def test_a_rejected_login_does_not_echo_the_address_as_markup(client):
    response = client.post("/login", data={"email": HOSTILE, "password": "x"})

    assert response.status_code == 400
    assert "<script>alert(1)" not in response.text
    assert "&lt;script&gt;" in response.text or "&#34;&gt;" in response.text


def test_the_basecoat_macros_still_render_what_they_mark_as_markup(client):
    """`| safe` in a macro is a promise that this part is HTML on purpose."""
    html = templates.env.from_string(
        '{% from "basecoat/dialog.html.jinja" import dialog %}'
        "{% call dialog(id='d', title='<em>Titulo</em>', description='texto') %}cuerpo{% endcall %}"
    ).render()

    assert "<em>Titulo</em>" in html


def test_plain_text_email_keeps_its_ampersands():
    """The text part of an email must not turn `&` in a link into `&amp;`."""
    message = render_email(
        "password_reset",
        to="ana@example.com",
        reset_url="https://example.com/reset?a=1&b=2",
        expires_in_minutes=30,
    )

    assert "a=1&b=2" in message.text
    assert "&amp;" not in message.text
    # ...while the HTML part is escaped, as it should be.
    assert "a=1&amp;b=2" in message.html
