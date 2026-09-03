"""Pydantic schemas: what the outside world is allowed to send in.

Kiro's forms are server-rendered, so these validate `application/x-www-form-
urlencoded` input rather than JSON. The router parses the raw fields, hands them
here, and renders the form again with `form_errors()` when validation fails.
"""

from app.schemas.base import form_errors

__all__ = ["form_errors"]
