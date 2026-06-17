# app/api/admin/routes_jobs.py
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import jdatetime

from app.db.session import get_db
from app.db.models.job import Job
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.tasks.generate_post import process_job_task

router = APIRouter(prefix="/jobs", tags=["admin-jobs"])
templates = Jinja2Templates(directory="app/templates")


def gregorian_to_jalali_str(dt):
    """Convert Gregorian datetime to Jalali string with Persian digits"""
    if not dt:
        return "-"

    jalali_date = jdatetime.datetime.fromgregorian(datetime=dt)

    persian_digits = {
        '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
        '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
    }

    date_str = jalali_date.strftime('%Y/%m/%d')
    time_str = jalali_date.strftime('%H:%M')

    # Convert to Persian digits
    for eng, per in persian_digits.items():
        date_str = date_str.replace(eng, per)
        time_str = time_str.replace(eng, per)

    return f"{date_str} {time_str}"


@router.get("/", response_class=HTMLResponse)
async def jobs_index(request: Request, db: AsyncSession = Depends(get_db)):
    """نمایش لیست تمام Jobها"""
    result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    jobs = result.scalars().all()

    # Convert dates to Jalali for each job
    for job in jobs:
        job.jalali_date = gregorian_to_jalali_str(job.created_at)

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

    # Add Jalali date
    job.jalali_date = gregorian_to_jalali_str(job.created_at)

    return templates.TemplateResponse(
        "admin/jobs/show.html",
        {
            "request": request,
            "job": job,
            "post": post,
            "media_assets": media_assets,
        }
    )


@router.get("/{job_id}/edit", response_class=HTMLResponse)
async def edit_job_form(request: Request, job_id: int, db: AsyncSession = Depends(get_db)):
    """فرم ویرایش Job"""
    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Only allow editing aborted or failed jobs
    if job.status not in ("aborted", "failed"):
        raise HTTPException(status_code=400, detail="Only aborted or failed jobs can be edited")

    return templates.TemplateResponse(
        "admin/jobs/edit.html",
        {"request": request, "job": job}
    )


@router.post("/{job_id}/update")
async def update_job(
    request: Request,
    job_id: int,
    topic: str = Form(..., min_length=3),
    text_instructions: str = Form(""),
    image_instructions: str = Form(""),
    blog_image_count: int = Form(1, ge=0, le=10),
    instagram_image_count: int = Form(1, ge=0, le=10),
    auto_publish: bool = Form(False),
    action: str = Form("save"),
    db: AsyncSession = Depends(get_db)
):
    """بروزرسانی Job و شروع مجدد در صورت نیاز"""
    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update job fields
    job.topic = topic
    job.text_instructions = text_instructions
    job.image_instructions = image_instructions
    job.blog_image_count = blog_image_count
    job.instagram_image_count = instagram_image_count
    job.auto_publish = auto_publish

    # If action is start, restart the job
    if action == "start":
        job.status = "pending"
        job.error_message = None
        await db.commit()

        # Send to Celery
        process_job_task.delay(job.id)

        # Check if AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({"status": "success", "message": "Job started successfully"})

        return RedirectResponse(url="/admin/jobs", status_code=303)

    # If action is save, just save changes (keep aborted status)
    await db.commit()

    # Check if AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Job updated successfully"})

    return RedirectResponse(url="/admin/jobs", status_code=303)


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


@router.post("/{job_id}/abort")
async def abort_job(job_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """لغو Job در حال اجرا"""
    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("pending", "processing"):
        raise HTTPException(status_code=400, detail="Only pending or processing jobs can be aborted")

    # Set job status to aborted
    job.status = "aborted"
    job.error_message = "کاربر فرآیند را لغو کرد"
    await db.commit()

    # Check if it's an AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Job aborted successfully"})

    return RedirectResponse(
        url="/admin/jobs/",
        status_code=303
    )


@router.post("/{job_id}/restart")
async def restart_job(job_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """شروع مجدد Job لغو شده"""
    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "aborted":
        raise HTTPException(status_code=400, detail="Only aborted jobs can be restarted")

    # Reset job to pending
    job.status = "pending"
    job.error_message = None
    await db.commit()

    # Send to Celery
    process_job_task.delay(job.id)

    # Check if it's an AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Job restarted successfully"})

    return RedirectResponse(
        url="/admin/jobs/",
        status_code=303
    )
