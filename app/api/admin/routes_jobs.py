# app/api/admin/routes_jobs.py
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models.job import Job
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.tasks.generate_post import process_job_task

router = APIRouter(prefix="/jobs", tags=["admin-jobs"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def jobs_index(request: Request, db: AsyncSession = Depends(get_db)):
    """نمایش لیست تمام Jobها"""
    result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    jobs = result.scalars().all()
    return templates.TemplateResponse(
        "admin/jobs/index.html",
        {"request": request, "jobs": jobs}
    )


@router.get("/create", response_class=HTMLResponse)
async def job_create_form(request: Request):
    """فرم ایجاد Job جدید"""
    return templates.TemplateResponse(
        "admin/jobs/create.html",
        {"request": request}
    )


@router.post("/")
async def create_job(
    request: Request,
    topic: str = Form(..., min_length=3),
    text_instructions: str = Form(""),
    image_instructions: str = Form(""),
    blog_image_count: int = Form(1, ge=0, le=10),
    instagram_image_count: int = Form(1, ge=0, le=10),
    auto_publish: bool = Form(False),
    db: AsyncSession = Depends(get_db)
):
    """ایجاد Job جدید و ارسال به Celery"""
    job = Job(
        topic=topic,
        text_instructions=text_instructions,
        image_instructions=image_instructions,
        blog_image_count=blog_image_count,
        instagram_image_count=instagram_image_count,
        auto_publish=auto_publish,
        status="pending"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # ارسال به Celery برای پردازش ناهمگام
    process_job_task.delay(job.id)

    return RedirectResponse(
        url=f"/admin/jobs/{job.id}",
        status_code=303
    )


@router.get("/{job_id}", response_class=HTMLResponse)
async def show_job(request: Request, job_id: int, db: AsyncSession = Depends(get_db)):
    """نمایش جزئیات Job و نتایج تولید محتوا"""
    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    post = None
    media_assets = []

    if job.post_id:
        result = await db.execute(select(Post).filter(Post.id == job.post_id))
        post = result.scalar_one_or_none()
        if post:
            result = await db.execute(
                select(MediaAsset)
                .filter(MediaAsset.post_id == post.id)
                .order_by(MediaAsset.sort_order)
            )
            media_assets = result.scalars().all()

    return templates.TemplateResponse(
        "admin/jobs/show.html",
        {
            "request": request,
            "job": job,
            "post": post,
            "media_assets": media_assets,
        }
    )


@router.post("/{job_id}/retry")
async def retry_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """تلاش مجدد برای پردازش Job ناموفق"""
    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("failed", "pending"):
        raise HTTPException(status_code=400, detail="Only failed or pending jobs can be retried")

    # پاک کردن خطاهای قبلی
    job.status = "pending"
    job.error_message = None
    await db.commit()

    # ارسال مجدد به Celery
    process_job_task.delay(job.id)

    return RedirectResponse(
        url=f"/admin/jobs/{job.id}",
        status_code=303
    )
