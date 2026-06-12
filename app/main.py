from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base
from app.api.public import routes as public_routes
from app.api.admin import (
    routes_auth, routes_dashboard, routes_jobs,
    routes_posts, routes_leads, routes_catalog,
)


templates = Jinja2Templates(directory="app/templates/public")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Do NOT create tables here — Alembic handles schema management.
    # If you need to ensure tables exist (e.g. dev without Alembic),
    # uncomment the next line:
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Botocharcoal",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_production is False else None,
    redoc_url="/redoc" if settings.is_production is False else None,
)

# Validation error handler — return JSON for API calls
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


# Custom 404 HTML handler for public pages
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 404:
        # Only return HTML 404 for public/admin paths (not API routes)
        path = request.url.path
        if not path.startswith("/docs") and not path.startswith("/redoc") and not path.startswith("/openapi.json"):
            return templates.TemplateResponse(
                "404.html", {"request": request}, status_code=404
            )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


class NotFoundMiddleware(BaseHTTPMiddleware):
    """Middleware to serve 404.html for any unmatched routes."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if response.status_code == 404:
            path = request.url.path
            # Serve 404.html for all public-facing 404s
            if not path.startswith("/docs") and not path.startswith("/redoc"):
                return HTMLResponse(
                    content=templates.TemplateResponse(
                        "404.html", {"request": request}
                    ).body.decode("utf-8"),
                    status_code=404,
                    headers=dict(response.headers),
                )
        return response

app.add_middleware(NotFoundMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)

app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(public_routes.router)
app.include_router(routes_auth.router, prefix="/admin")
app.include_router(routes_dashboard.router, prefix="/admin")
app.include_router(routes_jobs.router, prefix="/admin")
app.include_router(routes_posts.router, prefix="/admin")
app.include_router(routes_leads.router, prefix="/admin")
app.include_router(routes_catalog.router, prefix="/admin")
