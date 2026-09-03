"""Validation for the authentication forms.

Messages are in Spanish because they are rendered straight into the page. What
they must never do is reveal whether an account exists — that judgement lives in
`app/services/auth.py`, not here.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.config import get_settings


def _validate_password_length(password: str) -> str:
    """Enforce the configured minimum length.

    Length is the only rule. Composition rules ("one uppercase, one symbol")
    push people towards `Password1!` and are no longer recommended by NIST;
    a longer passphrase is stronger and easier to remember.
    """
    minimum = get_settings().password_min_length
    if len(password) < minimum:
        raise ValueError(f"La contraseña debe tener al menos {minimum} caracteres")
    return password


class LoginForm(BaseModel):
    """Credentials submitted by the login form.

    The password is not length-checked here: an old account may predate a raise
    in the minimum, and rejecting the form would lock its owner out.
    """

    email: EmailStr
    password: str = Field(min_length=1)


class RegisterForm(BaseModel):
    """A new account."""

    email: EmailStr
    password: str
    full_name: str = Field(default="", max_length=120)

    _check_password = field_validator("password")(_validate_password_length)


class ForgotPasswordForm(BaseModel):
    """A request for a reset link."""

    email: EmailStr


class ResetPasswordForm(BaseModel):
    """A new password, typed twice."""

    password: str
    password_confirm: str

    _check_password = field_validator("password")(_validate_password_length)

    @model_validator(mode="after")
    def _passwords_must_match(self) -> Self:
        if self.password != self.password_confirm:
            raise ValueError("Las contraseñas no coinciden")
        return self
