from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import settings


templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Botocharcoal",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)


# -----------------------------
# Validation errors (422)
# -----------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


# -----------------------------
# HTTP errors (403, 404 ...)
# -----------------------------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):

    if exc.status_code == 403:
        return templates.TemplateResponse(
            "public/errors/403.html",
            {"request": request},
            status_code=403,
        )

    if exc.status_code == 404:
        return templates.TemplateResponse(
            "public/errors/404.html",
            {"request": request},
            status_code=404,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# -----------------------------
# Internal server errors (500)
# -----------------------------

@app.exception_handler(Exception)
async def internal_server_error_handler(request: Request, exc: Exception):

    return templates.TemplateResponse(
        "public/errors/500.html",
        {"request": request},
        status_code=500,
    )


# -----------------------------
# Middleware
# -----------------------------

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts_list,
)


# -----------------------------
# Static / Media
# -----------------------------

app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# -----------------------------
# Routers
# -----------------------------

app.include_router(api_router)


# -----------------------------
# Root redirect
# -----------------------------

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/", status_code=307)
