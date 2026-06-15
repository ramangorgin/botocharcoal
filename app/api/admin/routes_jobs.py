"""
Botocharcoal Admin — Job Routes
================================
Job management, AI settings, and generation controls.
"""

import json
from datetime import date, datetime

import jdatetime
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.constants import JobStatus
from app.db.models.ai_settings import AISettings
from app.db.models.content_item import ContentItem
from app.db.models.job import Job
from app.db.models.media_asset import MediaAsset
from app.db.models.post import Post
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.job import JobCreateSchema
from app.services.job_service import create_job, get_job_content_items, list_jobs
from app.tasks.content_pipeline import run_content_pipeline

router = APIRouter()
templates = Jinja2Templates(directory="app/templates/admin")

PERSIAN_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']


def _to_persian_digits(text: str) -> str:
    return ''.join(PERSIAN_DIGITS[int(ch)] if ch.isdigit() else ch for ch in str(text))


def _jalali_date(dt: datetime | None) -> str:
    if not dt:
        return '-'
    return _to_persian_digits(jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d'))


def _jalali_for_input(gdate: date | None) -> str:
    if not gdate:
        return ''
    return jdatetime.date.fromgregorian(date=gdate).strftime('%Y/%m/%d')


def _parse_start_date(raw: str | None) -> date:
    value = (raw or '').strip()
    if not value:
        return date.today()

    normalized = ''.join(str('۰۱۲۳۴۵۶۷۸۹'.index(ch)) if ch in '۰۱۲۳۴۵۶۷۸۹' else ch for ch in value)
    try:
        if '/' in normalized:
            parts = normalized.split('/')
            if len(parts) == 3:
                jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
                return jdatetime.date(jy, jm, jd).togregorian()
        return date.fromisoformat(normalized)
    except Exception:
        return date.today()


@router.get('/ai-settings', response_class=HTMLResponse)
async def ai_settings_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    result = await db.execute(select(AISettings).limit(1))
    settings_obj = result.scalars().first()
    return templates.TemplateResponse('ai_settings.html', {'request': request, 'ai_settings': settings_obj})


@router.post('/ai-settings')
async def update_ai_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    form = await request.form()

    provider = (form.get('provider') or 'openai').strip()
    api_key = (form.get('api_key') or '').strip() or None
    api_base_url = (form.get('api_base_url') or '').strip() or None
    text_model = (form.get('text_model') or '').strip() or None
    image_model = (form.get('image_model') or '').strip() or None
    prompt_template = (form.get('prompt_template') or '').strip() or None

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
    return RedirectResponse('/admin/ai-settings?msg=saved', status_code=302)


@router.get('/jobs', response_class=HTMLResponse)
async def jobs_list_page(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    jobs = await list_jobs(db, limit=limit)

    for job in jobs:
        job.jalali_created = _jalali_date(job.created_at)
        job.jalali_start_date = _jalali_for_input(job.start_date)

        total_items_result = await db.execute(
            select(func.count(ContentItem.id)).where(ContentItem.job_id == job.id)
        )
        completed_items_result = await db.execute(
            select(func.count(ContentItem.id)).where(
                ContentItem.job_id == job.id,
                ContentItem.status == JobStatus.COMPLETED,
            )
        )
        job.total_items = total_items_result.scalar() or 0
        job.completed_items = completed_items_result.scalar() or 0

    return templates.TemplateResponse('jobs_list.html', {'request': request, 'jobs': jobs})


@router.get('/jobs/create', response_class=HTMLResponse)
async def job_create_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    result = await db.execute(select(AISettings).limit(1))
    ai_settings = result.scalars().first()
    today = jdatetime.date.fromgregorian(date=date.today()).strftime('%Y/%m/%d')
    return templates.TemplateResponse(
        'job_create.html',
        {'request': request, 'ai_settings': ai_settings, 'start_date': today},
    )


@router.post('/jobs/create')
async def create_job_route(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    form = await request.form()

    subject = (form.get('subject') or '').strip()
    instructions = (form.get('instructions') or '').strip() or None

    if not subject:
        return RedirectResponse('/admin/jobs/create?error=subject_required', status_code=302)

    try:
        duration_days = int(form.get('duration_days') or 1)
    except Exception:
        duration_days = 1

    try:
        items_per_day = int(form.get('items_per_day') or 1)
    except Exception:
        items_per_day = 1

    try:
        blog_image_count = int(form.get('blog_image_count') or 1)
    except Exception:
        blog_image_count = 1

    try:
        instagram_image_count = int(form.get('instagram_image_count') or 4)
    except Exception:
        instagram_image_count = 4

    start_date = _parse_start_date(form.get('start_date'))
    auto_publish_blog = form.get('auto_publish_blog') == 'on'
    job_type = (form.get('job_type') or 'general').strip() or 'general'

    schema = JobCreateSchema(
        subject=subject,
        instructions=instructions,
        duration_days=max(1, min(duration_days, 30)),
        start_date=start_date,
        items_per_day=max(1, min(items_per_day, 10)),
        auto_publish_blog=auto_publish_blog,
        blog_image_count=max(0, min(blog_image_count, 5)),
        instagram_image_count=max(1, min(instagram_image_count, 10)),
        job_type=job_type,
    )

    job = await create_job(schema, db)
    job.status = JobStatus.QUEUED
    await db.commit()
    await db.refresh(job)

    run_content_pipeline.delay(job.id)

    return RedirectResponse(f'/admin/jobs/{job.id}?msg=queued', status_code=302)


@router.get('/jobs/{job_id}', response_class=HTMLResponse)
async def job_detail(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    job = await db.get(Job, job_id)
    if not job:
        return HTMLResponse('Job not found', status_code=404)

    content_items = await get_job_content_items(job_id, db)

    completed_count = 0
    failed_count = 0
    for ci in content_items:
        if ci.status == JobStatus.COMPLETED:
            completed_count += 1
        elif ci.status == JobStatus.FAILED:
            failed_count += 1

    job.jalali_created = _jalali_date(job.created_at)

    return templates.TemplateResponse(
        'job_detail.html',
        {
            'request': request,
            'job': job,
            'content_items': content_items,
            'completed_count': completed_count,
            'failed_count': failed_count,
        },
    )


@router.post('/jobs/{job_id}/generate')
async def trigger_generate(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    job = await db.get(Job, job_id)
    if not job:
        return RedirectResponse('/admin/jobs', status_code=302)

    items = await get_job_content_items(job_id, db)
    for ci in items:
        ci.status = JobStatus.PENDING
        ci.instagram_caption = None
        ci.instagram_hashtags = None
        ci.instagram_image_urls = None
        ci.blog_title = None
        ci.blog_slug = None
        ci.blog_body = None
        ci.blog_image_urls = None
        ci.ai_response = None

    job.status = JobStatus.QUEUED
    job.error_message = None
    job.retry_count = (job.retry_count or 0) + 1
    await db.commit()

    run_content_pipeline.delay(job.id)
    return RedirectResponse(f'/admin/jobs/{job_id}?msg=restarted', status_code=302)


@router.post('/jobs/{job_id}/retry')
async def retry_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    job = await db.get(Job, job_id)
    if not job:
        return RedirectResponse('/admin/jobs', status_code=302)

    job.status = JobStatus.QUEUED
    job.error_message = None
    job.retry_count = (job.retry_count or 0) + 1
    await db.commit()

    run_content_pipeline.delay(job.id)
    return RedirectResponse(f'/admin/jobs/{job_id}?msg=retried', status_code=302)


@router.get('/jobs/{job_id}/download/{item_id}/instagram')
async def download_instagram_assets(
    job_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    ci = await db.get(ContentItem, item_id)
    if not ci or ci.job_id != job_id:
        return JSONResponse(status_code=404, content={'detail': 'محتوا یافت نشد'})

    image_urls: list[str] = []
    if ci.instagram_image_urls:
        try:
            image_urls = json.loads(ci.instagram_image_urls)
        except Exception:
            image_urls = []

    return JSONResponse(
        {
            'caption': ci.instagram_caption or '',
            'hashtags': ci.instagram_hashtags or '',
            'image_urls': image_urls,
            'blog_title': ci.blog_title or '',
        }
    )


@router.get('/jobs/{job_id}/download/{item_id}/blog')
async def download_blog_assets(
    job_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    ci = await db.get(ContentItem, item_id)
    if not ci or ci.job_id != job_id:
        return JSONResponse(status_code=404, content={'detail': 'محتوا یافت نشد'})

    image_urls: list[str] = []
    if ci.blog_image_urls:
        try:
            image_urls = json.loads(ci.blog_image_urls)
        except Exception:
            image_urls = []

    return JSONResponse(
        {
            'title': ci.blog_title or '',
            'slug': ci.blog_slug or '',
            'body': ci.blog_body or '',
            'image_urls': image_urls,
        }
    )


@router.post('/jobs/{job_id}/publish/{item_id}/blog')
async def publish_blog_post(
    job_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    ci = await db.get(ContentItem, item_id)
    if not ci or ci.job_id != job_id:
        return JSONResponse(status_code=404, content={'detail': 'محتوا یافت نشد'})

    if not ci.blog_title or not ci.blog_body:
        return JSONResponse(status_code=400, content={'detail': 'عنوان یا بدنه پست موجود نیست'})

    slug = ci.blog_slug or f'job-{job_id}-item-{item_id}'
    existing = await db.execute(select(Post).where(Post.slug == slug))
    if existing.scalars().first():
        return JSONResponse(status_code=409, content={'detail': 'پست با این slug قبلاً وجود دارد'})

    post = Post(
        topic=ci.blog_title,
        title=ci.blog_title,
        slug=slug,
        body_html=ci.blog_body,
        summary=(ci.blog_body or '')[:280],
        instagram_caption=ci.instagram_caption,
        hashtags=ci.instagram_hashtags,
        website_status='published',
        published_to_website_at=datetime.now(),
        instagram_status='not_published',
        source_type='ai',
        blog_enabled=True,
        instagram_enabled=bool(ci.instagram_caption or ci.instagram_hashtags),
        job_id=job_id,
        content_item_id=ci.id,
    )
    db.add(post)
    await db.flush()

    if ci.blog_image_urls:
        try:
            image_urls = json.loads(ci.blog_image_urls)
        except Exception:
            image_urls = []
        for i, url in enumerate(image_urls):
            db.add(
                MediaAsset(
                    post_id=post.id,
                    job_id=job_id,
                    role='blog_cover',
                    public_url=url,
                    sort_order=i,
                )
            )
        if image_urls:
            post.cover_image_url = image_urls[0]

    if ci.instagram_image_urls:
        try:
            image_urls = json.loads(ci.instagram_image_urls)
        except Exception:
            image_urls = []
        for i, url in enumerate(image_urls):
            db.add(
                MediaAsset(
                    post_id=post.id,
                    job_id=job_id,
                    role='instagram',
                    public_url=url,
                    sort_order=i,
                )
            )

    await db.commit()
    await db.refresh(post)

    return RedirectResponse(f'/admin/posts/{post.id}?msg=created_from_job', status_code=302)


@router.get('/jobs/{job_id}/copy/caption/{item_id}')
async def copy_instagram_caption(
    job_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    ci = await db.get(ContentItem, item_id)
    if not ci or ci.job_id != job_id:
        return JSONResponse(status_code=404, content={'detail': 'محتوا یافت نشد'})

    text = (ci.instagram_caption or '').strip()
    hashtags = (ci.instagram_hashtags or '').strip()
    joined = f"{text}\n\n{hashtags}".strip()
    return JSONResponse({'type': 'instagram_caption', 'text': joined})


@router.get('/jobs/{job_id}/copy/body/{item_id}')
async def copy_blog_body(
    job_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    ci = await db.get(ContentItem, item_id)
    if not ci or ci.job_id != job_id:
        return JSONResponse(status_code=404, content={'detail': 'محتوا یافت نشد'})

    return JSONResponse({'type': 'blog_body', 'title': ci.blog_title or '', 'body': ci.blog_body or ''})


@router.get('/jobs/{job_id}/content/{item_id}/publish')
async def publish_content_item_to_post(
    job_id: int,
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Open post_create pre-filled from a ContentItem's AI results."""
    ci = await db.get(ContentItem, item_id)
    if not ci or ci.job_id != job_id:
        return JSONResponse(status_code=404, content={'detail': 'محتوا یافت نشد'})

    # Build ig_image_urls_text for the textarea
    ig_text = ''
    if ci.instagram_image_urls:
        try:
            ig_urls = json.loads(ci.instagram_image_urls)
            ig_text = '\n'.join(u for u in ig_urls if u)
        except Exception:
            ig_text = ci.instagram_image_urls or ''

    return templates.TemplateResponse(
        'post_create.html',
        {
            'request': request,
            'post': None,
            'ci': ci,
            'source': 'job',
            'job_id': ci.job_id,
            'content_item_id': ci.id,
            'ig_image_urls_text': ig_text,
        },
    )
