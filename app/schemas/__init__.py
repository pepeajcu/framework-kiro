"""Pydantic schemas: what the outside world is allowed to send in.

Kiro's forms are server-rendered, so these validate `application/x-www-form-
urlencoded` input rather than JSON. The router parses the raw fields and hands them to
`validate_form()`, which returns the validated model or a `FormResult` that renders the
form again with the visitor's input and the errors.
"""

from app.schemas.base import FormResult, form_errors, validate_form

__all__ = ["FormResult", "form_errors", "validate_form"]
