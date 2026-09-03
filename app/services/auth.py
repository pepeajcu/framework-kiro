"""Authentication rules.

The reference example of a Kiro service: it owns decisions, not queries and not
HTTP. Routers translate its results into responses and cookies; repositories do
the talking to PostgreSQL.

Three rules run through everything here and are worth stating once:

1. **Never reveal whether an address has an account.** Login failures are one
   exception with one message, and requesting a reset link looks identical
   whether or not the address is known.
2. **Changing a password ends every session and every outstanding reset link.**
   Recovering an account is worth nothing if whoever took it stays logged in.
3. **Tokens are stored hashed.** The value in the cookie or in the emailed link
   exists in the database only as a SHA-256.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.config import Settings
from app.emails import EmailSender, render_email
from app.exceptions import ConflictError, InvalidCredentialsError, InvalidTokenError
from app.models.role import USER_ROLE
from app.models.user import User
from app.repositories.password_reset_token import PasswordResetTokenRepository
from app.repositories.user import RoleRepository, UserRepository, normalise_email
from app.repositories.user_session import UserSessionRepository
from app.security import (
    hash_password,
    hash_token,
    new_token,
    password_needs_rehash,
    verify_password,
    waste_time_verifying,
)

# How stale `last_seen_at` may get before a request refreshes it. Writing it on
# every request would turn every page view into a database write for no useful
# gain in precision.
LAST_SEEN_REFRESH = dt.timedelta(minutes=5)


class AuthService:
    """Everything that decides who someone is."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.sessions = UserSessionRepository(session)
        self.reset_tokens = PasswordResetTokenRepository(session)

    # --- Accounts ----------------------------------------------------------

    def register(self, *, email: str, password: str, full_name: str = "") -> User:
        """Create an account with the default role.

        Raises `ConflictError` if the address is taken. The caller must render
        that as a form error, never as a page that says "this email is already
        registered" to a stranger — see rule 1.
        """
        if self.users.email_exists(email):
            raise ConflictError(f"email already registered: {normalise_email(email)}")

        user = self.users.create(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name.strip(),
        )

        default_role = self.roles.get_by_slug(USER_ROLE)
        if default_role is not None:
            user.roles.append(default_role)
        self.session.flush()
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        """Return the user these credentials belong to.

        Raises `InvalidCredentialsError` for a wrong password, an unknown
        address and a disabled account alike.
        """
        user = self.users.get_by_email(email)

        if user is None:
            # Spend the same time as a real check would, so the response time
            # does not answer "does this address have an account?".
            waste_time_verifying()
            raise InvalidCredentialsError

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError

        if not user.is_active:
            raise InvalidCredentialsError

        # Free upgrade: if this hash predates a change in the argon2 parameters,
        # replace it now, while the plaintext is in hand and correct.
        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            self.session.flush()

        return user

    def set_password(self, user: User, password: str) -> None:
        """Change a password and close everything the old one could open."""
        user.password_hash = hash_password(password)
        self.session.flush()
        self.sessions.revoke_all_for_user(user.id)
        self.reset_tokens.invalidate_all_for_user(user.id)

    # --- Sessions ----------------------------------------------------------

    def start_session(self, user: User, *, ip_address: str = "", user_agent: str = "") -> str:
        """Open a session and return the token that belongs in the cookie.

        The raw token is returned once and never stored: from here on it exists
        in the browser and, as a hash, in the database.
        """
        token = new_token()
        expires_at = dt.datetime.now(tz=dt.UTC) + dt.timedelta(
            days=self.settings.session_lifetime_days
        )
        self.sessions.create(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=expires_at,
            ip_address=ip_address[:45],
            user_agent=user_agent[:255],
        )
        return token

    def resolve_session(self, token: str) -> User | None:
        """Return the user a session token belongs to, or None.

        None covers every failure — unknown, expired, revoked, disabled user —
        because from the caller's point of view they are the same situation:
        nobody is logged in.
        """
        session = self.sessions.get_by_token(token)
        if session is None or not session.is_usable():
            return None
        if not session.user.is_active:
            return None

        now = dt.datetime.now(tz=dt.UTC)
        if now - session.last_seen_at > LAST_SEEN_REFRESH:
            session.last_seen_at = now
            self.session.flush()

        return session.user

    def end_session(self, token: str) -> None:
        """Revoke one session. Unknown tokens are ignored, not an error."""
        session = self.sessions.get_by_token(token)
        if session is not None:
            self.sessions.revoke(session)

    # --- Password recovery -------------------------------------------------

    def request_password_reset(self, email: str, *, emailer: EmailSender) -> None:
        """Email a reset link, if the address belongs to an active account.

        Returns nothing in every case, including an unknown address. The caller
        renders the same confirmation either way: a form that answers "no such
        user" is a list of everyone who *is* a user.
        """
        user = self.users.get_by_email(email)
        if user is None or not user.is_active:
            return

        # Only one link at a time can be live. Otherwise every click on "I
        # forgot my password" leaves another working key in the inbox.
        self.reset_tokens.invalidate_all_for_user(user.id)

        token = new_token()
        ttl = dt.timedelta(minutes=self.settings.password_reset_ttl_minutes)
        self.reset_tokens.create(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=dt.datetime.now(tz=dt.UTC) + ttl,
        )

        emailer.send(
            render_email(
                "password_reset",
                to=user.email,
                reset_url=f"{self.settings.base_url.rstrip('/')}/reset-password/{token}",
                expires_in_minutes=self.settings.password_reset_ttl_minutes,
            )
        )

    def user_for_reset_token(self, token: str) -> User:
        """Return the account a reset link belongs to.

        Raises `InvalidTokenError` if the link is unknown, expired or already
        used. Called before showing the form, so an expired link says so instead
        of accepting a password it will then refuse to save.
        """
        record = self.reset_tokens.get_by_token(token)
        if record is None or not record.is_usable():
            raise InvalidTokenError
        return record.user

    def reset_password(self, token: str, new_password: str) -> User:
        """Spend a reset token and set the new password."""
        record = self.reset_tokens.get_by_token(token)
        if record is None or not record.is_usable():
            raise InvalidTokenError

        user = record.user
        self.reset_tokens.mark_used(record)
        # Revokes every session too: if somebody else was already inside the
        # account, this is the moment they are thrown out.
        self.set_password(user, new_password)
        return user
