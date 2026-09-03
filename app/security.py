"""Cryptographic primitives for authentication.

Everything here is small and stateless: hashing a password, minting an opaque
token, hashing it for storage, signing the session cookie. *When* to call each
one is a business rule and lives in `app/services/auth.py`.

Nothing else in the codebase should import `argon2`, `secrets` or `hashlib` for
these purposes. One module means one place to audit and one place to change the
parameters when the hardware moves on.
"""

from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Response
from itsdangerous import BadSignature, URLSafeSerializer

from app.config import Settings

# argon2id with the library defaults: 64 MiB of memory, 3 iterations, 4 lanes.
# Memory-hard by design — that is what makes a GPU farm a poor investment
# against these hashes, and what bcrypt cannot offer.
_hasher = PasswordHasher()

# Verified against when the email does not exist, so a login attempt for an
# unknown address costs the same as one for a real user. Without it, response
# time alone tells an attacker which addresses are registered.
_DUMMY_HASH = _hasher.hash("a password that is never anyone's")

SESSION_COOKIE_NAME = "session"

# Salts keep signatures for different purposes from being interchangeable, even
# though they share SECRET_KEY: a session cookie can never be replayed as
# anything else.
_SESSION_SALT = "kiro.session"


# --- Passwords ---------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Whether the password matches the hash.

    Returns False instead of raising, including for a malformed hash: a corrupt
    row must fail closed, as a rejected login, never as a 500 that reveals the
    account exists.
    """
    try:
        _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return True


def waste_time_verifying() -> None:
    """Spend the cost of a password check without having a password to check.

    Called on login attempts for addresses that do not exist, to keep the
    response time indistinguishable from a wrong password.
    """
    verify_password("wrong", _DUMMY_HASH)


def password_needs_rehash(password_hash: str) -> bool:
    """Whether this hash was made with weaker parameters than today's."""
    return _hasher.check_needs_rehash(password_hash)


# --- Opaque tokens -----------------------------------------------------------


def new_token() -> str:
    """Mint a random, URL-safe token with 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash an opaque token for storage.

    SHA-256 rather than argon2, on purpose. These tokens are 256 bits of
    randomness with nothing to guess, so a slow hash would buy nothing and cost
    64 MiB of memory on every single request. What hashing does buy: a leaked
    database dump contains no usable session cookie and no live reset link.
    """
    return hashlib.sha256(token.encode()).hexdigest()


# --- Session cookie ----------------------------------------------------------


def _serializer(settings: Settings) -> URLSafeSerializer:
    return URLSafeSerializer(settings.secret_key, salt=_SESSION_SALT)


def sign_session_token(token: str, settings: Settings) -> str:
    """Sign a session token for the cookie."""
    return _serializer(settings).dumps(token)


def unsign_session_token(value: str, settings: Settings) -> str | None:
    """Recover the token from a signed cookie, or None if it was tampered with.

    A failed signature also covers the case of a rotated `SECRET_KEY`, which is
    why rotating it logs everybody out — that is the documented emergency
    switch, not a side effect.
    """
    try:
        return _serializer(settings).loads(value)  # type: ignore[no-any-return]
    except BadSignature:
        return None


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    """Attach the session cookie to a response.

    Every flag here matters:

    - `httponly` keeps JavaScript — including anything injected by an XSS — from
      reading the cookie.
    - `secure` is on in any deployed environment, so the cookie never travels
      over plain HTTP. It is off locally because localhost is not HTTPS and the
      browser would silently drop the cookie.
    - `samesite="lax"` means the cookie is not sent on cross-site POSTs, which
      blocks the simplest form of CSRF while still surviving a normal link from
      an email.
    """
    response.set_cookie(
        SESSION_COOKIE_NAME,
        sign_session_token(token, settings),
        max_age=settings.session_lifetime_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Remove the session cookie.

    The flags must match the ones it was set with or the browser keeps the old
    cookie alongside the deletion.
    """
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", httponly=True, samesite="lax")
