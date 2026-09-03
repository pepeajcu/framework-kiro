"""Application entrypoint: builds and configures the FastAPI app.

Kiro renders every page server-side (SSR). Routers return HTML — full pages on
navigation, fragments on HTMX requests. JSON responses exist only for machine
consumers such as the health probe.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.exceptions import AuthenticationRequiredError, NotFoundError, PermissionDeniedError
from app.routers import auth, health, pages
from app.templating import STATIC_DIR, render


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Written as a factory so tests can construct an app with overridden settings
    instead of mutating global state.
    """
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        # Interactive docs are a development aid; never expose them in production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(pages.router)

    register_error_handlers(app)
    return app


def register_error_handlers(app: FastAPI) -> None:
    """Map domain exceptions and HTTP errors onto rendered HTML pages.

    Errors are rendered with the site's own layout rather than Starlette's
    plain-text default: a 404 is a page a visitor can act on, and Google indexes
    it like any other.
    """

    @app.exception_handler(AuthenticationRequiredError)
    def handle_authentication_required(request: Request, exc: Exception) -> Response:
        """Send anonymous visitors to the login form, remembering where they were."""
        next_url = exc.next_url if isinstance(exc, AuthenticationRequiredError) else "/"
        login_url = f"/login?next={quote(next_url, safe='/')}"

        # An HTMX request expects a fragment. Answering with a 303 would make it
        # swap the whole login page into a corner of the current one; the
        # HX-Redirect header navigates the browser instead.
        if request.headers.get("HX-Request") == "true":
            return Response(status_code=204, headers={"HX-Redirect": login_url})

        return RedirectResponse(login_url, status_code=303)

    @app.exception_handler(PermissionDeniedError)
    def handle_permission_denied(request: Request, exc: Exception) -> HTMLResponse:
        """Somebody is logged in, but this is not for them."""
        return render(request, "pages/403.html", status_code=403)

    @app.exception_handler(NotFoundError)
    def handle_not_found(request: Request, exc: NotFoundError) -> HTMLResponse:
        return render(request, "pages/404.html", status_code=404)

    @app.exception_handler(404)
    def handle_http_404(request: Request, exc: Exception) -> HTMLResponse:
        return render(request, "pages/404.html", status_code=404)

    @app.exception_handler(500)
    def handle_http_500(request: Request, exc: Exception) -> HTMLResponse:
        return render(request, "pages/500.html", status_code=500)


app = create_app()
