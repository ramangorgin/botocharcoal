# app/api/admin/routes_jobs.py
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi.templating import Jinja2Templates
from typing import Optional
import logging
from pathlib import Path

from app.db.session import get_db
from app.db.models.job import Job
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.api.admin.dependencies import get_current_admin
from app.tasks.generate_post import process_job_task

logger = logging.getLogger(__name__)
router = APIRouter()

# Fix template directory - use absolute path or correct relative path
# Option 1: Use absolute path (recommended)
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Goes up to app/
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Option 2: Or if you want to keep relative path, use:
# templates = Jinja2Templates(directory="app/templates")


@router.get("/jobs", response_class=HTMLResponse)
async def list_jobs(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    query = select(Job).order_by(desc(Job.created_at))

    if status:
        query = query.where(Job.status == status)

    # Get total count for pagination
    count_query = select(Job)
    if status:
        count_query = count_query.where(Job.status == status)
    result = await db.execute(count_query)
    total = result.scalars().all()
    total_count = len(total)

    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    return templates.TemplateResponse(
        "admin/jobs/index.html",  # Note: full path from templates directory
        {
            "request": request,
            "jobs": jobs,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_count": total_count,
            "current_status": status,
        },
    )


@router.get("/jobs/create", response_class=HTMLResponse)
async def create_job_form(
    request: Request,
    user=Depends(get_current_admin),
):
    return templates.TemplateResponse(
        "admin/jobs/create.html",
        {
            "request": request,
        },
    )


@router.post("/jobs")
async def create_job(
    request: Request,
    topic: str = Form(...),
    blog_text_instructions: str = Form(""),
    blog_image_instructions: str = Form(""),
    instagram_text_instructions: str = Form(""),
    instagram_image_instructions: str = Form(""),
    blog_image_count: int = Form(1),
    instagram_image_count: int = Form(1),
    auto_publish: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    try:
        # Create job with separate instructions
        job = Job(
            topic=topic,
            blog_text_instructions=blog_text_instructions,
            blog_image_instructions=blog_image_instructions,
            instagram_text_instructions=instagram_text_instructions,
            instagram_image_instructions=instagram_image_instructions,
            blog_image_count=blog_image_count,
            instagram_image_count=instagram_image_count,
            auto_publish=auto_publish,
            status="pending",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        logger.info(f"✅ Job created: id={job.id}, topic='{job.topic}'")

        # Send to Celery for processing
        process_job_task.delay(job.id)
        logger.info(f"📤 Job {job.id} sent to Celery")

        # Check if it's an AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({
                "status": "success",
                "message": "Job created successfully",
                "redirect": f"/admin/jobs/{job.id}"
            })

        # Redirect to job detail page
        return RedirectResponse(f"/admin/jobs/{job.id}", status_code=303)

    except Exception as e:
        logger.error(f"❌ Failed to create job: {str(e)}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({
                "status": "error",
                "message": str(e)
            }, status_code=500)
        return RedirectResponse("/admin/jobs?error=failed", status_code=303)


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def show_job(
    request: Request,
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=404
        )

    post = None
    media_assets = []

    if job.post_id:
        post_result = await db.execute(select(Post).where(Post.id == job.post_id))
        post = post_result.scalar_one_or_none()

        if post:
            assets_result = await db.execute(
                select(MediaAsset).where(MediaAsset.post_id == post.id).order_by(MediaAsset.sort_order)
            )
            media_assets = assets_result.scalars().all()

    return templates.TemplateResponse(
        "admin/jobs/show.html",
        {
            "request": request,
            "job": job,
            "post": post,
            "media_assets": media_assets,
        },
    )


@router.get("/jobs/{job_id}/edit", response_class=HTMLResponse)
async def edit_job_form(
    request: Request,
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=404
        )

    return templates.TemplateResponse(
        "admin/jobs/edit.html",
        {
            "request": request,
            "job": job,
        },
    )


@router.post("/jobs/{job_id}/abort")
async def abort_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if job and job.status in ("pending", "processing"):
        job.status = "aborted"
        await db.commit()
        return JSONResponse({"status": "success"})

    return JSONResponse({"status": "error", "message": "Cannot abort this job"}, status_code=400)


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if job and job.status == "failed":
        job.status = "pending"
        job.error_message = None
        await db.commit()
        process_job_task.delay(job.id)
        return JSONResponse({"status": "success"})

    return JSONResponse({"status": "error", "message": "Cannot retry this job"}, status_code=400)


@router.post("/jobs/{job_id}/restart")
async def restart_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if job and job.status == "aborted":
        job.status = "pending"
        job.error_message = None
        await db.commit()
        process_job_task.delay(job.id)
        return JSONResponse({"status": "success"})

    return JSONResponse({"status": "error", "message": "Cannot restart this job"}, status_code=400)
