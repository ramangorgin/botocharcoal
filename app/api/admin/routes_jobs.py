"""
Botocharcoal Admin — Job Routes
================================
Full CRUD for Jobs, AI Settings, and content generation controls.
"""

import json
from datetime import datetime, timezone, date
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.job import Job
from app.db.models.content_item import ContentItem
from app.db.models.ai_settings import AISettings
from app.api.deps import get_current_admin
from app.services.job_service import (
    create_job, list_jobs, get_job, get_job_content_items,
)
from app.tasks.content_pipeline import run_content_pipeline
from app.core.constants import JobStatus
from app.schemas.job import JobCreateSchema

router = APIRouter()
templates = Jinja2Templates(directory="app/templates/admin")


# ============================================================
# AI Settings Routes
# ============================================================

@router.get("/ai-settings", response_class=HTMLResponse)
async def ai_settings_page(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    result = await db.execute(select(AISettings).limit(1))
    settings_obj = result.scalars().first()
    return templates.TemplateResponse("ai_settings.html", {
        "request": request,
        "ai_settings": settings_obj,
    })


@router.post("/ai-settings")
async def update_ai_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    form = await request.form()
    
    provider = form.get("provider", "openai")
    api_key = form.get("api_key", "").strip() or None
    api_base_url = form.get("api_base_url", "").strip() or None
    text_model = form.get("text_model", "").strip() or None
    image_model = form.get("image_model", "").strip() or None
    prompt_template = form.get("prompt_template", "").strip() or None

    result = await db.execute(select(AISettings).limit(1))
    existing = result.scalars().first()

    if existing:
        existing.provider = provider
        if api_key:
            existing.api_key = api_key
        existing.api_base_url = api_base_url
        existing.text_model = text_model
        existing.image_model = image_model
        existing.prompt_template = prompt_template
    else:
        existing = AISettings(
            provider=provider,
            api_key=api_key,
            api_base_url=api_base_url,
            text_model=text_model,
            image_model=image_model,
            prompt_template=prompt_template,
        )
        db.add(existing)

    await db.commit()
    return RedirectResponse("/admin/ai-settings?msg=saved", status_code=302)


# ============================================================
# Jobs List
# ============================================================

@router.get("/jobs", response_class=HTMLResponse)
async def jobs_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
    limit: int = Query(default=50),
):
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).limit(limit)
    )
    jobs = result.scalars().all()
    
    # Enrich jobs with content item counts and Jalali dates
    for job in jobs:
        if job.created_at:
            import jdatetime
            jdt = jdatetime.datetime.fromgregorian(datetime=job.created_at)
            jalali_str = jdt.strftime('%Y/%m/%d')
            persian_digits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']
            job.jalali_created = ''.join(persian_digits[int(d)] if d.isdigit() else d for d in jalali_str)
        else:
            job.jalali_created = '-'
        
        # Convert start_date to Jalali for display
        if job.start_date:
            import jdatetime
            jdt = jdatetime.date.fromgregorian(date=job.start_date)
            jalali_str = jdt.strftime('%Y/%m/%d')
            job.jalali_start_date = ''.join(persian_digits[int(d)] if d.isdigit() else d for d in jalali_str)
        else:
            job.jalali_start_date = '-'
        
        items_result = await db.execute(
            select(func.count(ContentItem.id)).where(ContentItem.job_id == job.id)
        )
        job.total_items = items_result.scalar() or 0
        
        completed_result = await db.execute(
            select(func.count(ContentItem.id)).where(
                ContentItem.job_id == job.id,
                ContentItem.status == JobStatus.COMPLETED.value
            )
        )
        job.completed_items = completed_result.scalar() or 0
    
    return templates.TemplateResponse("jobs_list.html", {
        "request": request,
        "jobs": jobs,
    })


# ============================================================
# Job Create
# ============================================================

@router.get("/jobs/create", response_class=HTMLResponse)
async def job_create_page(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    # Pre-load AI settings for the form hint
    result = await db.execute(select(AISettings).limit(1))
    ai_settings = result.scalars().first()
    return templates.TemplateResponse("job_create.html", {
        "request": request,
        "ai_settings": ai_settings,
    })


@router.post("/jobs/create")
async def create_job_route(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    form = await request.form()
    subject = form.get("subject", "").strip()
    instructions = form.get("instructions", "").strip() or None
    
    # Parse duration_days
    try:
        duration_days = int(form.get("duration_days", 1))
    except (ValueError, TypeError):
        duration_days = 1
    
    # Parse items_per_day
    try:
        items_per_day = int(form.get("items_per_day", 1))
    except (ValueError, TypeError):
        items_per_day = 1
    
    # Parse start_date (Jalali to Gregorian)
    start_date_str = form.get("start_date", "")
    try:
        if start_date_str:
            # JalaliDatepicker sends YYYY/MM/DD format
            jalali_parts = start_date_str.split('/')
            if len(jalali_parts) == 3:
                jalali_year = int(jalali_parts[0].replace('۰', '0').replace('۱', '1').replace('۲', '2').replace('۳', '3').replace('۴', '4').replace('۵', '5').replace('۶', '6').replace('۷', '7').replace('۸', '8').replace('۹', '9'))
                jalali_month = int(jalali_parts[1].replace('۰', '0').replace('۱', '1').replace('۲', '2').replace('۳', '3').replace('۴', '4').replace('۵', '5').replace('۶', '6').replace('۷', '7').replace('۸', '8').replace('۹', '9'))
                jalali_day = int(jalali_parts[2].replace('۰', '0').replace('۱', '1').replace('۲', '2').replace('۳', '3').replace('۴', '4').replace('۵', '5').replace('۶', '6').replace('۷', '7').replace('۸', '8').replace('۹', '9'))
                import jdatetime
                start_date = jdatetime.date(jalali_year, jalali_month, jalali_day).togregorian()
            else:
                start_date = date.today()
        else:
            start_date = date.today()
    except (ValueError, TypeError):
        start_date = date.today()
    
    # Parse booleans
    auto_publish_blog = form.get("auto_publish_blog") == "on"
    blog_image_count = int(form.get("blog_image_count", 1))
    instagram_image_count = int(form.get("instagram_image_count", 4))
    job_type = form.get("job_type", "general")
    
    # Validate
    if not subject:
        return RedirectResponse("/admin/jobs/create?error=subject_required", status_code=302)
    
    schema = JobCreateSchema(
        subject=subject,
        instructions=instructions,
        duration_days=duration_days,
        start_date=start_date,
        items_per_day=items_per_day,
        auto_publish_blog=auto_publish_blog,
        blog_image_count=blog_image_count,
        instagram_image_count=instagram_image_count,
        job_type=job_type,
    )
    
    job = await create_job(schema, db)
    job.status = JobStatus.QUEUED
    await db.commit()
    await db.refresh(job)
    
    # Queue the pipeline task
    run_content_pipeline.delay(job.id)
    
    return RedirectResponse(f"/admin/jobs/{job.id}?msg=queued", status_code=302)


# ============================================================
# Job Detail
# ============================================================

@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    job = await db.get(Job, job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)
    
    # Get content items
    result = await db.execute(
        select(ContentItem)
        .where(ContentItem.job_id == job_id)
        .order_by(ContentItem.day_number, ContentItem.id)
    )
    content_items = result.scalars().all()
    
    # Count statuses
    completed_count = 0
    processing_count = 0
    failed_count = 0
    for ci in content_items:
        if ci.status == JobStatus.COMPLETED.value:
            completed_count += 1
        elif ci.status == JobStatus.PROCESSING.value:
            processing_count += 1
        elif ci.status == JobStatus.FAILED.value:
            failed_count += 1
    
    # Jalali date for job created
    if job.created_at:
        import jdatetime
        jdt = jdatetime.datetime.fromgregorian(datetime=job.created_at)
        jalali_str = jdt.strftime('%Y/%m/%d')
        persian_digits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']
        job.jalali_created = ''.join(persian_digits[int(d)] if d.isdigit() else d for d in jalali_str)
    else:
        job.jalali_created = '-'
    
    return templates.TemplateResponse("job_detail.html", {
        "request": request,
        "job": job,
        "content_items": content_items,
        "completed_count": completed_count,
        "processing_count": processing_count,
        "failed_count": failed_count,
    })


# ============================================================
# Job Actions (Generate, Retry)
# ============================================================

@router.post("/jobs/{job_id}/generate")
async def trigger_generate(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    job = await db.get(Job, job_id)
    if not job:
        return RedirectResponse(f"/admin/jobs/{job_id}", status_code=302)
    
    # Reset all content items to PENDING and job to QUEUED
    await db.execute(
        select(ContentItem).where(ContentItem.job_id == job_id)
    )
    
    result = await db.execute(
        select(ContentItem).where(ContentItem.job_id == job_id)
    )
    items = result.scalars().all()
    for ci in items:
        ci.status = JobStatus.PENDING
        ci.blog_title = None
        ci.blog_slug = None
        ci.blog_body = None
        ci.instagram_caption = None
        ci.instagram_hashtags = None
        ci.instagram_image_urls = None
        ci.blog_image_urls = None
        ci.ai_response = None
    
    job.status = JobStatus.QUEUED
    job.error_message = None
    job.retry_count += 1
    await db.commit()
    
    run_content_pipeline.delay(job.id)
    return RedirectResponse(f"/admin/jobs/{job_id}?msg=restarted", status_code=302)


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    job = await db.get(Job, job_id)
    if not job:
        return RedirectResponse(f"/admin/jobs/{job_id}", status_code=302)
    
    job.status = JobStatus.QUEUED
    job.error_message = None
    job.retry_count += 1
    await db.commit()
    
    run_content_pipeline.delay(job.id)
    return RedirectResponse(f"/admin/jobs/{job_id}?msg=retried", status_code=302)


# ============================================================
# Content Item Download / Copy helpers (AJAX)
# ============================================================

@router.get("/jobs/{job_id}/download/{item_id}/instagram")
async def download_instagram_assets(
    job_id: int,
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    ci = await db.get(ContentItem, item_id)
    if not ci or ci.job_id != job_id:
        return JSONResponse(status_code=404, content={"detail": "محتوا یافت نشد"})
    
    # Parse image URLs from JSON
    image_urls = []
    if ci.instagram_image_urls:
        try:
            image_urls = json.loads(ci.instagram_image_urls)
        except json.JSONDecodeError:
            pass
    
    return JSONResponse({
        "caption": ci.instagram_caption or "",
        "hashtags": ci.instagram_hashtags or "",
        "image_urls": image_urls,
        "blog_title": ci.blog_title or "",
    })


@router.get("/jobs/{job_id}/download/{item_id}/blog")
async def download_blog_assets(
    job_id: int,
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    ci = await db.get(ContentItem, item_id)
    if not ci or ci.job_id != job_id:
        return JSONResponse(status_code=404, content={"detail": "محتوا یافت نشد"})
    
    image_urls = []
    if ci.blog_image_urls:
        try:
            image_urls = json.loads(ci.blog_image_urls)
        except json.JSONDecodeError:
            pass
    
    return JSONResponse({
        "title": ci.blog_title or "",
        "slug": ci.blog_slug or "",
        "body": ci.blog_body or "",
        "image_urls": image_urls,
    })


@router.post("/jobs/{job_id}/publish/{item_id}/blog")
async def publish_blog_post(
    job_id: int,
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Manually publish a blog post from a content item."""
    ci = await db.get(ContentItem, item_id)
    if not ci or ci.job_id != job_id:
        return JSONResponse(status_code=404, content={"detail": "محتوا یافت نشد"})
    
    if not ci.blog_title or not ci.blog_body:
        return JSONResponse(status_code=400, content={"detail": "عنوان یا بدنه مقاله موجود نیست"})
    
    # Check for existing post with same slug
    from app.db.models.post import Post
    existing = await db.execute(select(Post).where(Post.slug == ci.blog_slug))
    
    if existing.scalars().first():
        return JSONResponse(status_code=409, content={"detail": "مقاله‌ای با این slug قبلاً وجود دارد"})
    
    post = Post(
        topic=ci.blog_title,
        title=ci.blog_title,
        slug=ci.blog_slug or "",
        body_html=ci.blog_body,
        instagram_caption=ci.instagram_caption or "",
        hashtags=ci.instagram_hashtags or "",
        website_status="published",
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    
    # Save image assets if available
    if ci.blog_image_urls:
        try:
            image_urls = json.loads(ci.blog_image_urls)
            for i, url in enumerate(image_urls):
                db.add(MediaAsset(
                    post_id=post.id,
                    job_id=job_id,
                    role=MediaRole.BLOG_COVER,
                    prompt=f"Blog cover for {ci.blog_title}",
                    local_path="",
                    public_url=url,
                    sort_order=i,
                ))
            await db.commit()
        except (json.JSONDecodeError, Exception) as e:
            pass
    
    return RedirectResponse(f"/admin/jobs/{job_id}?msg=blog_published", status_code=302)


# ============================================================
# Copy helpers (AJAX endpoints for copying content)
# ============================================================

@router.get("/jobs/{job_id}/copy/caption/{item_id}")
async def copy_instagram_caption(
    job_id: int,
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    ci = await db.get(ContentItem, item_id)
    if not ci or ci.job_id != job_id:
        return JSONResponse(status_code=404, content={"detail": "محتوا یافت نشد"})
    
    return JSONResponse({
        "type": "instagram_caption",
        "text": f"{ci.instagram_caption or ''}\n.\n.\n.\n{ci.instagram_hashtags or ''}",
    })


@router.get("/jobs/{job_id}/copy/body/{item_id}")
async def copy_blog_body(
    job_id: int,
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    ci = await db.get(ContentItem, item_id)
    if not ci or ci.job_id != job_id:
        return JSONResponse(status_code=404, content={"detail": "محتوا یافت نشد"})
    
    return JSONResponse({
        "type": "blog_body",
        "title": ci.blog_title or "",
        "body": ci.blog_body or "",
    })
