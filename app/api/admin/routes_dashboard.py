from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi.templating import Jinja2Templates

from app.db.session import get_db
from app.db.models import Post
from app.api.admin.dependencies import get_current_admin

router = APIRouter()

templates = Jinja2Templates(directory="app/templates/admin")


@router.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):

    total_posts = await db.execute(
        select(func.count(Post.id))
    )

    published_posts = await db.execute(
        select(func.count(Post.id))
        .where(Post.website_status == "published")
    )

    drafts = await db.execute(
        select(func.count(Post.id))
        .where(Post.website_status == "draft")
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "total_posts": total_posts.scalar(),
            "published_posts": published_posts.scalar(),
            "draft_posts": drafts.scalar(),
        },
    )
