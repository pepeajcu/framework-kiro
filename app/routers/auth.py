"""Login, registration and password recovery.

Plain HTML forms, not HTMX. Signing in is the one flow that has to work when
JavaScript does not — a browser extension, a locked-down corporate machine, a
CDN that dropped one file — because everything else is behind it.

Every POST answers with a 303 redirect on success (post/redirect/get), so a
refresh after logging in does not re-submit the form, and with a re-rendered
form carrying a 400 on failure.
"""

from __future__ import annotations

import datetime as dt
import ipaddress
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from app.analytics import AnalyticsEvent
from app.config import Settings
from app.deps import Analytics, AppSettings, DbSession, Emailer, OptionalUser
from app.emails import deliver_email
from app.exceptions import ConflictError, InvalidCredentialsError, InvalidTokenError
from app.schemas import validate_form
from app.schemas.auth import ForgotPasswordForm, LoginForm, RegisterForm, ResetPasswordForm
from app.security import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    set_session_cookie,
    unsign_session_token,
)
from app.services.auth import AuthService
from app.services.consent import CONSENT_COOKIE, has_marketing_consent
from app.services.rate_limit import (
    RateLimit,
    RateLimiter,
    login_buckets,
    password_reset_buckets,
)
from app.templating import render

router = APIRouter(tags=["auth"], include_in_schema=False)

# 303 rather than 302: it tells the browser to follow up with a GET, which is
# the whole point of post/redirect/get. A 302 lets it repeat the POST.
SEE_OTHER = 303
TOO_MANY_REQUESTS = 429

RATE_LIMITED_MESSAGE = "Demasiados intentos. Espera unos minutos y vuelve a probar."


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


@lru_cache(maxsize=8)
def _parse_trusted_proxies(
    spec: str,
) -> tuple[
    bool,
    frozenset[ipaddress.IPv4Address | ipaddress.IPv6Address],
    tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...],
    frozenset[str],
]:
    """Parse `FORWARDED_ALLOW_IPS` into addresses, networks and literal hostnames."""
    entries = [item.strip() for item in spec.split(",") if item.strip()]
    if "*" in entries:
        return True, frozenset(), (), frozenset()

    hosts: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    literals: set[str] = {"testclient"}
    for entry in entries:
        if "/" in entry:
            try:
                networks.append(ipaddress.ip_network(entry, strict=False))
                continue
            except ValueError:
                pass
        try:
            hosts.add(ipaddress.ip_address(entry))
        except ValueError:
            literals.add(entry)
    return False, frozenset(hosts), tuple(networks), frozenset(literals)


def _is_trusted_proxy(host: str, spec: str) -> bool:
    """Whether `host` is a reverse proxy we trust to set `X-Forwarded-For`."""
    if not host:
        return False
    trust_all, hosts, networks, literals = _parse_trusted_proxies(spec)
    if trust_all:
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return host in literals
    return addr in hosts or any(addr in net for net in networks)


def _client_fingerprint(request: Request, settings: Settings | None = None) -> tuple[str, str]:
    """The real client IP (through trusted proxies only) and user agent."""
    peer = request.client.host if request.client else ""
    app_settings: Settings | None = settings or getattr(request.app.state, "settings", None)
    allow_ips = (
        app_settings.forwarded_allow_ips
        if app_settings is not None
        else "127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    )

    ip = peer
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for and _is_trusted_proxy(peer, allow_ips):
        chain = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
        if chain:
            # Walk right-to-left: each trusted proxy appends to the end, so the
            # first non-trusted hop from the right is the real connecting client.
            ip = chain[0]
            for hop in reversed(chain):
                if not _is_trusted_proxy(hop, allow_ips):
                    ip = hop
                    break

    return ip, request.headers.get("user-agent", "")


def _track_signal(
    background_tasks: BackgroundTasks,
    analytics: Analytics,
    request: Request,
    *,
    name: str,
    email: str,
    ip: str,
    user_agent: str,
) -> None:
    """Fire an analytics event in the background, only with consent.

    `add_task` runs after the response is sent, so a slow or unreachable
    analytics endpoint can never add latency to a login or a signup. Skipped
    entirely without consent — see `app.services.consent`.
    """
    if not has_marketing_consent(request.cookies.get(CONSENT_COOKIE)):
        return
    background_tasks.add_task(
        analytics.track,
        AnalyticsEvent(name=name, email=email, ip_address=ip, user_agent=user_agent),
    )


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
    background_tasks: BackgroundTasks,
    analytics: Analytics,
    user: OptionalUser,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    next_url: Annotated[str, Form(alias="next")] = "/",
) -> Response:
    """Check the credentials and open a session."""
    target = safe_next_url(next_url)
    service = AuthService(db, settings)
    form = validate_form(LoginForm, email=email, password=password)

    ip, user_agent = _client_fingerprint(request, settings)
    limiter = RateLimiter(db)
    buckets = login_buckets(ip=ip, email=email)
    limit = RateLimit(
        max_attempts=settings.login_max_attempts,
        window=dt.timedelta(minutes=settings.login_window_minutes),
    )

    # Checked before validating anything: the point of the limit is to stop
    # spending an argon2 verification per attempt, and that is the expensive
    # part an attacker is trying to make us repeat.
    if limiter.is_blocked(buckets, limit):
        return render(
            request,
            "pages/auth/login.html",
            {"form": form.with_errors({"__all__": RATE_LIMITED_MESSAGE}), "next": target},
            status_code=TOO_MANY_REQUESTS,
        )

    if form.data is None:
        return render(
            request, "pages/auth/login.html", {"form": form, "next": target}, status_code=400
        )
    try:
        account = service.authenticate(email=form.data.email, password=form.data.password)
    except InvalidCredentialsError:
        # Only real credential failures count. A malformed address never reached
        # a password check, and counting typos would lock people out of their
        # own accounts for spelling.
        limiter.record(buckets)
        # One message for a wrong password, an unknown address and a disabled
        # account. Which one it was is not the visitor's business unless they
        # own the account.
        return render(
            request,
            "pages/auth/login.html",
            {
                "form": form.with_errors({"__all__": "Email o contraseña incorrectos"}),
                "next": target,
            },
            status_code=400,
        )

    # Only clear the account's own email bucket: clearing the IP bucket would let
    # an attacker reset their IP counter after 9 failed guesses against a victim
    # simply by logging into an account of their own.
    limiter.reset([f"login:email:{account.email}"[:128]])
    token = service.start_session(account, ip_address=ip, user_agent=user_agent)
    _track_signal(
        background_tasks,
        analytics,
        request,
        name="login",
        email=account.email,
        ip=ip,
        user_agent=user_agent,
    )

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
    clear_session_cookie(response, settings)
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
    background_tasks: BackgroundTasks,
    analytics: Analytics,
    user: OptionalUser,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    full_name: Annotated[str, Form()] = "",
) -> Response:
    """Create an account and log the new user straight in."""
    _guard_registration(settings)
    service = AuthService(db, settings)
    form = validate_form(RegisterForm, email=email, password=password, full_name=full_name)
    if form.data is None:
        return render(request, "pages/auth/register.html", {"form": form}, status_code=400)

    try:
        account = service.register(
            email=form.data.email,
            password=form.data.password,
            full_name=form.data.full_name,
        )
    except ConflictError:
        # Registration cannot hide that an address is taken — the account has to
        # go somewhere — so it says so on the email field and offers the way in.
        return render(
            request,
            "pages/auth/register.html",
            {"form": form.with_errors({"email": "Ya existe una cuenta con este email"})},
            status_code=400,
        )

    ip, user_agent = _client_fingerprint(request, settings)
    token = service.start_session(account, ip_address=ip, user_agent=user_agent)
    _track_signal(
        background_tasks,
        analytics,
        request,
        name="sign_up",
        email=account.email,
        ip=ip,
        user_agent=user_agent,
    )

    response = RedirectResponse("/", status_code=SEE_OTHER)
    set_session_cookie(response, token, settings)
    return response


# --- Password recovery ------------------------------------------------------


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_form(request: Request, user: OptionalUser) -> Response:
    """The "email me a link" form."""
    return render(request, "pages/auth/forgot_password.html")


@router.get("/forgot-password/sent", response_class=HTMLResponse)
def forgot_password_sent(request: Request, user: OptionalUser) -> Response:
    """Confirmation page after requesting a password reset link."""
    return render(request, "pages/auth/forgot_password_sent.html")


@router.post("/forgot-password", response_class=HTMLResponse)
def forgot_password(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    background_tasks: BackgroundTasks,
    emailer: Emailer,
    user: OptionalUser,
    email: Annotated[str, Form()] = "",
) -> Response:
    """Send a reset link, and redirect to the same confirmation page either way."""
    form = validate_form(ForgotPasswordForm, email=email)
    if form.data is None:
        return render(request, "pages/auth/forgot_password.html", {"form": form}, status_code=400)

    ip, _ = _client_fingerprint(request, settings)
    limiter = RateLimiter(db)
    buckets = password_reset_buckets(ip=ip, email=form.data.email)
    limit = RateLimit(
        max_attempts=settings.password_reset_max_requests,
        window=dt.timedelta(minutes=settings.password_reset_window_minutes),
    )

    # Every request here puts a message in somebody's inbox, so the limit is
    # tighter and counts every attempt, not just the failed ones. Without it the
    # form is a way to have a stranger's mailbox flooded.
    if limiter.is_blocked(buckets, limit):
        return render(
            request,
            "pages/auth/forgot_password.html",
            {"form": form.with_errors({"__all__": RATE_LIMITED_MESSAGE})},
            status_code=TOO_MANY_REQUESTS,
        )
    limiter.record(buckets)

    message = AuthService(db, settings).request_password_reset(form.data.email)
    if message is not None:
        background_tasks.add_task(deliver_email, emailer, message)

    # Post/Redirect/Get (303) to the same confirmation page whether or not the
    # address exists, so refreshing never re-submits the form.
    return RedirectResponse("/forgot-password/sent", status_code=SEE_OTHER)


@router.get("/reset-password/{token}", response_class=HTMLResponse)
def reset_password_form(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    user: OptionalUser,
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
    user: OptionalUser,
    token: str,
    password: Annotated[str, Form()] = "",
    password_confirm: Annotated[str, Form()] = "",
) -> Response:
    """Set the new password and log the user in on this browser only."""
    service = AuthService(db, settings)

    form = validate_form(ResetPasswordForm, password=password, password_confirm=password_confirm)
    if form.data is None:
        return render(
            request,
            "pages/auth/reset_password.html",
            {"form": form, "token": token},
            status_code=400,
        )

    try:
        account = service.reset_password(token, form.data.password)
    except InvalidTokenError:
        return render(request, "pages/auth/reset_password_invalid.html", status_code=400)

    # `reset_password` revoked every session this account had, this browser
    # included. Opening a fresh one is what makes the flow end logged in
    # rather than back at the login form.
    ip, user_agent = _client_fingerprint(request, settings)
    new_session = service.start_session(account, ip_address=ip, user_agent=user_agent)

    response = RedirectResponse("/", status_code=SEE_OTHER)
    set_session_cookie(response, new_session, settings)
    return response
