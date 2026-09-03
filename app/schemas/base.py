"""Helpers shared by every schema."""

from __future__ import annotations

from pydantic import ValidationError


def form_errors(exc: ValidationError) -> dict[str, str]:
    """Turn a `ValidationError` into `{field: message}` for a template.

    Only the first error per field survives, which is what a form should show:
    a list of five complaints about one password teaches nobody anything.
    """
    errors: dict[str, str] = {}
    for error in exc.errors():
        field = str(error["loc"][0]) if error["loc"] else "__all__"
        errors.setdefault(field, error["msg"])
    return errors
