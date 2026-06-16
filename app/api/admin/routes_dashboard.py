from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi.templating import Jinja2Templates

from app.db.session import get_db
from app.db.models import Post # فرض می‌کنیم از اینجا استفاده میشه
# از dependencies.py هم get_current_admin رو داریم
from app.api.admin.dependencies import get_current_admin

router = APIRouter()

templates = Jinja2Templates(directory="app/templates/admin")


# این تابع الان وضعیت دیتابیس رو هم چک میکنه
async def check_db_health(db: AsyncSession) -> bool:
    try:
        # یک کوئری ساده برای چک کردن اتصال
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
    # چک کردن وضعیت دیتابیس
    db_is_healthy = await check_db_health(db)

    # محاسبهٔ آمارهای مربوط به پست‌ها
    total_posts_count = await db.execute(select(func.count(Post.id)))
    published_posts_count = await db.execute(
        select(func.count(Post.id)).where(Post.website_status == "published")
    )
    drafts_count = await db.execute(
        select(func.count(Post.id)).where(Post.website_status == "draft")
    )

    # ارسال داده‌ها به template
    # حالا health شامل وضعیت دیتابیس میشه
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "total_posts": total_posts_count.scalar(),
            "published_posts": published_posts_count.scalar(),
            "draft_posts": drafts_count.scalar(),
            # این متغیر رو به template می‌فرستیم
            # که در dashboard.html با {% if health %} چک میشه
            "health": {
                "database": db_is_healthy
            }
        },
    )
