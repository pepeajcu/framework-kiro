"""Application entrypoint: builds and configures the FastAPI app.

Kiro renders every page server-side (SSR). Routers return HTML — full pages on
navigation, fragments on HTMX requests. JSON responses exist only for machine
consumers such as the health probe.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.exceptions import (
    AuthenticationRequiredError,
    CsrfError,
    NotFoundError,
    PermissionDeniedError,
)
from app.hypermedia import error_response
from app.logs import configure_logging
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.csrf import CsrfCookieMiddleware, csrf_guard
from app.middleware.request_id import REQUEST_ID_HEADER, RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware, apply_security_headers
from app.routers import auth, consent, design, health, notes, pages, seo
from app.templating import STATIC_DIR, is_htmx


def create_app(settings: Settings | None = None, *, enforce_csrf: bool = True) -> FastAPI:
    """Build the FastAPI application.

    Written as a factory so tests can construct an app with overridden settings
    instead of mutating global state.

    `enforce_csrf=False` is for the test suite only — see `app/middleware/csrf.py`
    for why it is a parameter here and not an environment variable.
    """
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        # Interactive docs are a development aid; never expose them in production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
        # A global dependency, so a new route is protected by existing rather
        # than by remembering to add something to it.
        dependencies=[Depends(csrf_guard(enforce=enforce_csrf))],
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Added inner-to-outer: Starlette runs the LAST one added first, so the
    # request id is bound before anything else can log, and the security headers
    # land on every response including the ones the CSRF check rejects.
    app.add_middleware(CsrfCookieMiddleware, settings=settings)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(consent.router)
    app.include_router(seo.router)
    app.include_router(notes.router)
    app.include_router(pages.router)
    if settings.design_preview_enabled:
        # Development only: in a deployed environment the route does not exist.
        app.include_router(design.router)

    register_error_handlers(app, settings)
    return app


def register_error_handlers(app: FastAPI, settings: Settings) -> None:
    """Map domain exceptions and HTTP errors onto rendered HTML pages.

    Errors are rendered with the site's own layout rather than Starlette's
    plain-text default: a 404 is a page a visitor can act on, and Google indexes
    it like any other.
    """

    # Every handler below answers a navigation with a page and an HTMX call with
    # a toast (app/hypermedia.py), always with the same status code: a fragment
    # swap that gets a whole 404 document is worse than a one-line message.

    @app.exception_handler(CsrfError)
    def handle_csrf(request: Request, exc: Exception) -> HTMLResponse:
        """A form arrived without a valid token."""
        return error_response(
            request,
            "pages/403.html",
            status_code=403,
            title="El formulario ha caducado",
            description="Recarga la página y vuelve a enviarlo.",
            context={"reason": "csrf"},
        )

    @app.exception_handler(RequestValidationError)
    def handle_validation(request: Request, exc: Exception) -> HTMLResponse:
        """A parameter that is not what the route declared (a malformed id).

        FastAPI's default is a JSON 422, which nobody reading a web page can
        use. Form fields are validated by our own schemas and re-rendered with
        their errors; this is only what is left over.
        """
        return error_response(
            request,
            "pages/400.html",
            status_code=400,
            title="Solicitud no válida",
            description="No hemos entendido lo que se pidió.",
        )

    @app.exception_handler(AuthenticationRequiredError)
    def handle_authentication_required(request: Request, exc: Exception) -> Response:
        """Send anonymous visitors to the login form, remembering where they were."""
        next_url = exc.next_url if isinstance(exc, AuthenticationRequiredError) else "/"
        login_url = f"/login?next={quote(next_url, safe='/')}"

        # An HTMX request expects a fragment. Answering with a 303 would make it
        # swap the whole login page into a corner of the current one; the
        # HX-Redirect header navigates the browser instead.
        if is_htmx(request):
            return Response(status_code=204, headers={"HX-Redirect": login_url})

        return RedirectResponse(login_url, status_code=303)

    @app.exception_handler(PermissionDeniedError)
    def handle_permission_denied(request: Request, exc: Exception) -> HTMLResponse:
        """Somebody is logged in, but this is not for them."""
        return error_response(
            request,
            "pages/403.html",
            status_code=403,
            title="Sin permiso",
            description="Tu cuenta no tiene acceso a esto.",
        )

    @app.exception_handler(NotFoundError)
    def handle_not_found(request: Request, exc: NotFoundError) -> HTMLResponse:
        return error_response(
            request,
            "pages/404.html",
            status_code=404,
            title="No encontrado",
            description="Lo que buscas ya no existe.",
        )

    @app.exception_handler(405)
    def handle_http_405(request: Request, exc: Exception) -> HTMLResponse:
        """The address exists but not for this method: say so as a page, keep `Allow`."""
        response = error_response(
            request,
            "pages/405.html",
            status_code=405,
            title="Acción no permitida",
            description="Esa acción no está permitida aquí.",
        )
        allow = getattr(exc, "headers", None) or {}
        if "Allow" in allow:
            response.headers["Allow"] = allow["Allow"]
        return response

    @app.exception_handler(404)
    def handle_http_404(request: Request, exc: Exception) -> HTMLResponse:
        return error_response(
            request,
            "pages/404.html",
            status_code=404,
            title="No encontrado",
            description="Lo que buscas no existe.",
        )

    @app.exception_handler(500)
    def handle_http_500(request: Request, exc: Exception) -> HTMLResponse:
        request_id = getattr(request.state, "request_id", None)
        response = error_response(
            request,
            "pages/500.html",
            status_code=500,
            title="Algo se rompió por nuestra parte",
            # With the id, "it did not work" becomes one line to look up in the
            # logs, the same as the 500 page prints.
            description=f"Referencia: {request_id}" if request_id else "Inténtalo de nuevo.",
        )
        # Starlette answers an unhandled exception from outside the middleware
        # stack, so the request id and the security headers that every other
        # response gets on the way out have to be put on by hand here.
        if request_id:
            response.headers[REQUEST_ID_HEADER] = request_id
        apply_security_headers(response, settings)
        return response


app = create_app()
