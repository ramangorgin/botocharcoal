from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.job import Job
from app.db.models.post import Post
from app.db.models.lead import Lead
from app.api.deps import get_current_admin
from app.services.health_service import check_health

router = APIRouter()
templates = Jinja2Templates(directory="app/templates/admin")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    total_posts = (await db.execute(select(func.count(Post.id)))).scalar()
    total_leads = (await db.execute(select(func.count(Lead.id)))).scalar()
    recent_jobs = (await db.execute(select(Job).order_by(Job.created_at.desc()).limit(5))).scalars().all()
    
    # Add Jalali dates and convert English numbers to Persian for jobs
    persian_digits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']
    def to_persian(n):
        return ''.join(persian_digits[int(d)] if d.isdigit() else d for d in str(n))
    
    for job in recent_jobs:
        if job.created_at:
            import jdatetime
            jdt = jdatetime.datetime.fromgregorian(datetime=job.created_at)
            jalali_str = jdt.strftime('%Y/%m/%d')
            job.jalali_created = ''.join(persian_digits[int(d)] if d.isdigit() else d for d in jalali_str)
        else:
            job.jalali_created = '-'
    
    health = await check_health(db)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_posts": to_persian(total_posts),
        "total_leads": to_persian(total_leads),
        "recent_jobs": recent_jobs,
        "health": health,
    })


@router.get("/health", response_class=JSONResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    health = await check_health(db)
    return health.model_dump()
