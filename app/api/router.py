from fastapi import APIRouter

from app.api.public.routes import router as public_router
from app.api.admin.routes_auth import router as auth_router
from app.api.admin.routes_dashboard import router as dashboard_router
from app.api.admin.routes_jobs import router as jobs_router
from app.api.admin.routes_posts import router as posts_router
from app.api.admin.routes_ai_settings import router as ai_settings_router

api_router = APIRouter()

# Public
api_router.include_router(public_router)

# Admin
api_router.include_router(auth_router, prefix="/admin")
api_router.include_router(dashboard_router, prefix="/admin")
api_router.include_router(jobs_router, prefix="/admin")
api_router.include_router(posts_router, prefix="/admin")
api_router.include_router(ai_settings_router, prefix="/admin")
