# app/api/admin/routes_dashboard.py - Fixed version
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.models.post import Post
from app.db.models.job import Job
from app.api.admin.dependencies import get_current_admin
from app.core.template_config import templates

router = APIRouter()


async def check_db_health(db: AsyncSession) -> bool:
    try:
        await db.execute(select(func.now()))
        return True
    except Exception:
        return False


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    # Check database health
    db_is_healthy = await check_db_health(db)

    # Get post statistics
    total_result = await db.execute(select(func.count(Post.id)))
    total_posts = total_result.scalar() or 0

    published_result = await db.execute(
        select(func.count(Post.id)).where(Post.website_status == "published")
    )
    published_posts = published_result.scalar() or 0

    drafts_result = await db.execute(
        select(func.count(Post.id)).where(Post.website_status == "draft")
    )
    draft_posts = drafts_result.scalar() or 0

    # Get recent jobs
    jobs_result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).limit(5)
    )
    recent_jobs = jobs_result.scalars().all()

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "total_posts": total_posts,
            "published_posts": published_posts,
            "draft_posts": draft_posts,
            "recent_jobs": recent_jobs,
            "health": {
                "database": db_is_healthy
            }
        },
    )
