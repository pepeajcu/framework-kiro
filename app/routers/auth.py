"""Login, registration and password recovery.

Plain HTML forms, not HTMX. Signing in is the one flow that has to work when
JavaScript does not — a browser extension, a locked-down corporate machine, a
CDN that dropped one file — because everything else is behind it.

Every POST answers with a 303 redirect on success (post/redirect/get), so a
refresh after logging in does not re-submit the form, and with a re-rendered
form carrying a 400 on failure.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.deps import AppSettings, DbSession, Emailer, OptionalUser
from app.exceptions import ConflictError, InvalidCredentialsError, InvalidTokenError
from app.schemas import form_errors
from app.schemas.auth import ForgotPasswordForm, LoginForm, RegisterForm, ResetPasswordForm
from app.security import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    set_session_cookie,
    unsign_session_token,
)
from app.services.auth import AuthService
from app.templating import render

router = APIRouter(tags=["auth"], include_in_schema=False)

# 303 rather than 302: it tells the browser to follow up with a GET, which is
# the whole point of post/redirect/get. A 302 lets it repeat the POST.
SEE_OTHER = 303


def safe_next_url(candidate: str | None) -> str:
    """Sanitise a `?next=` parameter into a path on this site.

    Anything that is not a plain absolute path becomes "/". Without this check,
    `/login?next=https://evil.example` turns the site's own login form into a
    credible redirect to somebody else's — the classic open redirect, and a
    phishing link that passes every "is the domain right?" check.
    """
    if not candidate or not candidate.startswith("/") or candidate.startswith("//"):
        return "/"
    return candidate


def _client_fingerprint(request: Request) -> tuple[str, str]:
    """The IP and user agent to record on a session, for the user to recognise."""
    ip = request.client.host if request.client else ""
    return ip, request.headers.get("user-agent", "")


# --- Login ------------------------------------------------------------------


@router.get("/login", response_class=HTMLResponse)
def login_form(
    request: Request,
    user: OptionalUser,
    next_url: Annotated[str, Query(alias="next")] = "/",
) -> Response:
    """The login form."""
    if user is not None:
        return RedirectResponse(safe_next_url(next_url), status_code=SEE_OTHER)
    return render(request, "pages/auth/login.html", {"next": safe_next_url(next_url)})


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    next_url: Annotated[str, Form(alias="next")] = "/",
) -> Response:
    """Check the credentials and open a session."""
    target = safe_next_url(next_url)
    service = AuthService(db, settings)

    try:
        form = LoginForm(email=email, password=password)
        user = service.authenticate(email=form.email, password=form.password)
    except ValidationError as exc:
        return render(
            request,
            "pages/auth/login.html",
            {"errors": form_errors(exc), "email": email, "next": target},
            status_code=400,
        )
    except InvalidCredentialsError:
        # One message for a wrong password, an unknown address and a disabled
        # account. Which one it was is not the visitor's business unless they
        # own the account.
        return render(
            request,
            "pages/auth/login.html",
            {
                "errors": {"__all__": "Email o contraseña incorrectos"},
                "email": email,
                "next": target,
            },
            status_code=400,
        )

    ip, user_agent = _client_fingerprint(request)
    token = service.start_session(user, ip_address=ip, user_agent=user_agent)

    response = RedirectResponse(target, status_code=SEE_OTHER)
    set_session_cookie(response, token, settings)
    return response


@router.post("/logout")
def logout(request: Request, db: DbSession, settings: AppSettings) -> Response:
    """Close the current session.

    POST, not GET: a link would be followed by every prefetcher and email
    scanner out there, logging people out for no reason.
    """
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie is not None:
        token = unsign_session_token(cookie, settings)
        if token is not None:
            AuthService(db, settings).end_session(token)

    response = RedirectResponse("/", status_code=SEE_OTHER)
    clear_session_cookie(response)
    return response


# --- Registration -----------------------------------------------------------


def _guard_registration(settings: AppSettings) -> None:
    """Make the registration routes disappear when the project does not want them.

    A 404 rather than a 403: on a site where accounts are created by an
    administrator, /register should not exist at all.
    """
    if not settings.allow_registration:
        raise HTTPException(status_code=404)


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request, settings: AppSettings, user: OptionalUser) -> Response:
    """The registration form."""
    _guard_registration(settings)
    if user is not None:
        return RedirectResponse("/", status_code=SEE_OTHER)
    return render(request, "pages/auth/register.html")


@router.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    full_name: Annotated[str, Form()] = "",
) -> Response:
    """Create an account and log the new user straight in."""
    _guard_registration(settings)
    service = AuthService(db, settings)
    submitted = {"email": email, "full_name": full_name}

    try:
        form = RegisterForm(email=email, password=password, full_name=full_name)
        user = service.register(
            email=form.email,
            password=form.password,
            full_name=form.full_name,
        )
    except ValidationError as exc:
        return render(
            request,
            "pages/auth/register.html",
            {"errors": form_errors(exc), **submitted},
            status_code=400,
        )
    except ConflictError:
        # Registration cannot hide that an address is taken — the account has to
        # go somewhere — so it says so on the email field and offers the way in.
        return render(
            request,
            "pages/auth/register.html",
            {"errors": {"email": "Ya existe una cuenta con este email"}, **submitted},
            status_code=400,
        )

    ip, user_agent = _client_fingerprint(request)
    token = service.start_session(user, ip_address=ip, user_agent=user_agent)

    response = RedirectResponse("/", status_code=SEE_OTHER)
    set_session_cookie(response, token, settings)
    return response


# --- Password recovery ------------------------------------------------------


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_form(request: Request, user: OptionalUser) -> Response:
    """The "email me a link" form."""
    return render(request, "pages/auth/forgot_password.html")


@router.post("/forgot-password", response_class=HTMLResponse)
def forgot_password(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    emailer: Emailer,
    email: Annotated[str, Form()] = "",
) -> Response:
    """Send a reset link, and say the same thing either way."""
    try:
        form = ForgotPasswordForm(email=email)
    except ValidationError as exc:
        return render(
            request,
            "pages/auth/forgot_password.html",
            {"errors": form_errors(exc), "email": email},
            status_code=400,
        )

    AuthService(db, settings).request_password_reset(form.email, emailer=emailer)

    # Always the same page, whether or not the address exists. A form that
    # answers "we have no such user" is a way to enumerate every user.
    return render(request, "pages/auth/forgot_password_sent.html", {"email": form.email})


@router.get("/reset-password/{token}", response_class=HTMLResponse)
def reset_password_form(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    token: str,
) -> Response:
    """The "choose a new password" form, if the link is still good."""
    try:
        AuthService(db, settings).user_for_reset_token(token)
    except InvalidTokenError:
        return render(request, "pages/auth/reset_password_invalid.html", status_code=400)

    return render(request, "pages/auth/reset_password.html", {"token": token})


@router.post("/reset-password/{token}", response_class=HTMLResponse)
def reset_password(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    token: str,
    password: Annotated[str, Form()] = "",
    password_confirm: Annotated[str, Form()] = "",
) -> Response:
    """Set the new password and log the user in on this browser only."""
    service = AuthService(db, settings)

    try:
        form = ResetPasswordForm(password=password, password_confirm=password_confirm)
    except ValidationError as exc:
        return render(
            request,
            "pages/auth/reset_password.html",
            {"errors": form_errors(exc), "token": token},
            status_code=400,
        )

    try:
        user = service.reset_password(token, form.password)
    except InvalidTokenError:
        return render(request, "pages/auth/reset_password_invalid.html", status_code=400)

    # `reset_password` revoked every session this account had, this browser
    # included. Opening a fresh one is what makes the flow end logged in
    # rather than back at the login form.
    ip, user_agent = _client_fingerprint(request)
    new_session = service.start_session(user, ip_address=ip, user_agent=user_agent)

    response = RedirectResponse("/", status_code=SEE_OTHER)
    set_session_cookie(response, new_session, settings)
    return response
