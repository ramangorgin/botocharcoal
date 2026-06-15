import json
from datetime import datetime, timezone

import jdatetime
from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.models.content_item import ContentItem
from app.db.models.job import Job
from app.db.models.media_asset import MediaAsset
from app.db.models.post import Post
from app.db.models.user import User
from app.db.session import get_db
from app.services.media_storage import save_upload
from app.services.website_publish import publish_post_to_website, unpublish_post

router = APIRouter()
templates = Jinja2Templates(directory="app/templates/admin")

PERSIAN_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']


def _to_persian_digits(text: str) -> str:
    return ''.join(PERSIAN_DIGITS[int(ch)] if ch.isdigit() else ch for ch in str(text))


def _format_jalali(dt: datetime | None) -> str:
    if not dt:
        return '-'
    jdt = jdatetime.datetime.fromgregorian(datetime=dt)
    return _to_persian_digits(jdt.strftime('%Y/%m/%d'))


def _normalize_website_status(raw: str | None) -> str:
    val = (raw or 'draft').strip().lower()
    if val in {'published', 'publish', 'public', 'پابلیش'}:
        return 'published'
    if val in {'published', 'draft'}:
        return val
    if val == 'PUBLISHED':
        return 'published'
    if val == 'DRAFT':
        return 'draft'
    return 'draft'


def _parse_publish_date(raw: str | None) -> datetime | None:
    value = (raw or '').strip()
    if not value:
        return None

    # ISO support
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        pass

    # Jalali YYYY/MM/DD support
    try:
        normalized = ''.join(str('۰۱۲۳۴۵۶۷۸۹'.index(ch)) if ch in '۰۱۲۳۴۵۶۷۸۹' else ch for ch in value)
        parts = normalized.split('/')
        if len(parts) == 3:
            jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
            gdate = jdatetime.date(jy, jm, jd).togregorian()
            return datetime(gdate.year, gdate.month, gdate.day, tzinfo=timezone.utc)
    except Exception:
        return None

    return None


def _normalize_hashtags(raw_values: list[str], fallback: str = '') -> str | None:
    tags: list[str] = []
    candidates = raw_values or []
    if fallback:
        candidates.extend(fallback.replace(',', ' ').split())

    for item in candidates:
        if not item:
            continue
        for part in item.replace(',', ' ').split():
            token = part.strip()
            if not token:
                continue
            if not token.startswith('#'):
                token = '#' + token
            if token not in tags:
                tags.append(token)

    return ' '.join(tags) if tags else None


def _clean_text(form, key: str) -> str | None:
    value = form.get(key)
    if value is None:
        return None
    out = str(value).strip()
    return out or None


async def _save_upload_if_any(upload: UploadFile | None, subfolder: str) -> tuple[str, str] | None:
    if not upload:
        return None
    if not upload.filename:
        return None
    content = await upload.read()
    if not content:
        return None
    return await save_upload(content, upload.filename, subfolder=subfolder)


def _save_images_from_urls(urls: list[str], post_id: int, role: str, db: AsyncSession, sort_start: int = 0):
    """Create MediaAsset rows from URL strings."""
    for i, url in enumerate(urls):
        url = url.strip()
        if not url:
            continue
        db.add(
            MediaAsset(
                post_id=post_id,
                role=role,
                public_url=url,
                sort_order=sort_start + i,
            )
        )


@router.get('/posts', response_class=HTMLResponse)
async def posts_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    posts = (await db.execute(select(Post).order_by(Post.created_at.desc()))).scalars().all()
    for post in posts:
        post.jalali_date = _format_jalali(post.created_at)
    return templates.TemplateResponse('posts_list.html', {'request': request, 'posts': posts})


# --------------------------------------------------------------------------- #
#  POST CREATE — supports both manual and "from job content item"           #
# --------------------------------------------------------------------------- #

@router.get('/posts/create', response_class=HTMLResponse)
async def post_create_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Manual post creation OR pre-filled from a job's content item."""
    job_id = request.query_params.get('job_id')
    content_item_id = request.query_params.get('content_item_id')

    ci = None
    job = None
    if job_id and content_item_id:
        try:
            ci = await db.get(ContentItem, int(content_item_id))
            if ci:
                job = await db.get(Job, int(job_id))
        except Exception:
            pass

    context = {'request': request, 'post': None}
    if ci:
        # Build ig_image_urls_text for the textarea
        ig_text = ''
        if ci.instagram_image_urls:
            try:
                ig_urls = json.loads(ci.instagram_image_urls)
                ig_text = '\n'.join(u for u in ig_urls if u)
            except Exception:
                ig_text = ci.instagram_image_urls or ''
        context.update({
            'ci': ci,
            'source': 'job',
            'job_id': ci.job_id,
            'content_item_id': ci.id,
            'ig_image_urls_text': ig_text,
        })
        if job:
            context['job'] = job

    return templates.TemplateResponse('post_create.html', context)


@router.post('/posts/create')
async def post_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    form = await request.form()

    source = _clean_text(form, 'source')  # 'job' or None
    job_id_raw = _clean_text(form, 'job_id')
    content_item_id_raw = _clean_text(form, 'content_item_id')

    blog_enabled = 'blog_enabled' in form or 'blogEnabled' in form
    instagram_enabled = 'instagram_enabled' in form or 'instagramEnabled' in form

    if not blog_enabled and not instagram_enabled:
        return RedirectResponse('/admin/posts/create?error=empty_channels', status_code=302)

    # ---- resolve source content item ------------------------------------ #
    ci: ContentItem | None = None
    if source == 'job' and job_id_raw and content_item_id_raw:
        try:
            ci = await db.get(ContentItem, int(content_item_id_raw))
        except Exception:
            pass

    # ---- build values — prefilled from CI when available ---------------- #
    topic = _clean_text(form, 'topic')
    if not topic and ci:
        topic = (ci.blog_title or '').strip() or 'بدون موضوع'
    if not topic:
        topic = 'بدون موضوع'

    title = _clean_text(form, 'title')
    if not title:
        if blog_enabled:
            title = topic
        else:
            title = topic + ' (اینستاگرام)'

    slug = _clean_text(form, 'slug')
    if not slug:
        slug = slugify(title)

    existing = await db.execute(select(Post).where(Post.slug == slug))
    if existing.scalars().first():
        slug = f'{slug}-{int(datetime.now().timestamp())}'

    website_status = _normalize_website_status(_clean_text(form, 'website_status')) if blog_enabled else 'draft'
    publish_date = _parse_publish_date(_clean_text(form, 'publish_date')) if blog_enabled else None

    # Poster
    poster = _clean_text(form, 'poster')

    hashtags_raw = form.getlist('hashtags') if hasattr(form, 'getlist') else []
    hashtags = _normalize_hashtags(hashtags_raw, fallback=str(form.get('hashtags') or ''))

    post = Post(
        topic=topic,
        title=title,
        slug=slug,
        body_html=_clean_text(form, 'body_html') if blog_enabled else None,
        summary=_clean_text(form, 'summary') if blog_enabled else None,
        category=_clean_text(form, 'category') if blog_enabled else None,
        poster=poster,
        website_status=website_status,
        instagram_status='not_published',
        meta_title=_clean_text(form, 'meta_title') if blog_enabled else None,
        meta_description=_clean_text(form, 'meta_description') if blog_enabled else None,
        og_title=_clean_text(form, 'og_title') if blog_enabled else None,
        og_description=_clean_text(form, 'og_description') if blog_enabled else None,
        source_type='manual' if source != 'job' else 'ai',
        blog_enabled=blog_enabled,
        instagram_enabled=instagram_enabled,
        published_to_website_at=publish_date if website_status in ('published', 'PUBLISHED') else None,
    )

    # Instagram-specific
    if instagram_enabled:
        post.instagram_caption = _clean_text(form, 'instagram_caption') or (ci.instagram_caption if ci else None)
        post.hashtags = hashtags or (ci.instagram_hashtags if ci else None)
    else:
        post.instagram_caption = None
        post.hashtags = None
        post.instagram_status = 'not_published'

    # SEO images
    if blog_enabled:
        # OG image from file upload or URL
        og_upload = form.get('og_image_file')
        saved_og = await _save_upload_if_any(og_upload, subfolder='posts/og') if og_upload else None
        if saved_og:
            _, og_url = saved_og
            post.og_image = og_url
        else:
            post.og_image = _clean_text(form, 'og_image')

    db.add(post)
    await db.flush()

    # ---- Blog cover image: file upload, URL, or from CI ----------------- #
    if blog_enabled:
        blog_cover_url = None

        # 1. Try uploaded file (blog_image_file)
        blog_upload = form.get('blog_image_file')
        if blog_upload and blog_upload.filename:
            content = await blog_upload.read()
            if content:
                saved = await save_upload(content, blog_upload.filename, subfolder='posts/covers')
                if saved:
                    _, public_url = saved
                    blog_cover_url = public_url
                    db.add(
                        MediaAsset(
                            post_id=post.id,
                            role='blog_cover',
                            local_path=saved[0],
                            public_url=public_url,
                            sort_order=0,
                        )
                    )

        # 2. Try URL input
        if not blog_cover_url:
            blog_cover_url = _clean_text(form, 'blog_image_url')

        # 3. Fall back to CI blog_image_urls
        if not blog_cover_url and ci and ci.blog_image_urls:
            try:
                img_urls = json.loads(ci.blog_image_urls)
                for img_url in img_urls:
                    img_url = (img_url or '').strip()
                    if img_url:
                        blog_cover_url = img_url
                        db.add(
                            MediaAsset(
                                post_id=post.id,
                                role='blog_cover',
                                public_url=img_url,
                                sort_order=0,
                            )
                        )
                        break
            except Exception:
                pass

        if blog_cover_url:
            post.cover_image_url = blog_cover_url

    # ---- Instagram images: uploaded files + URL lines + CI fallback ----- #
    if instagram_enabled:
        sort_order = 0

        # 1. Uploaded files
        ig_files = form.getlist('ig_image_file') if hasattr(form, 'getlist') else []
        # FastAPI form.getlist returns the same list, but we need unique files
        seen_files = set()
        for upload in ig_files:
            if not upload.filename:
                continue
            if id(upload) in seen_files:
                continue
            seen_files.add(id(upload))
            saved = await _save_upload_if_any(upload, subfolder='posts/instagram')
            if saved:
                db.add(
                    MediaAsset(
                        post_id=post.id,
                        role='instagram',
                        local_path=saved[0],
                        public_url=saved[1],
                        sort_order=sort_order,
                    )
                )
                sort_order += 1

        # 2. URL lines
        ig_urls_raw = str(form.get('ig_image_urls') or '').strip()
        if ig_urls_raw:
            for line in ig_urls_raw.splitlines():
                url = line.strip()
                if url:
                    db.add(
                        MediaAsset(
                            post_id=post.id,
                            role='instagram',
                            public_url=url,
                            sort_order=sort_order,
                        )
                    )
                    sort_order += 1

        # 3. CI fallback
        if sort_order == 0 and ci and ci.instagram_image_urls:
            try:
                img_urls = json.loads(ci.instagram_image_urls)
                for img_url in img_urls:
                    img_url = (img_url or '').strip()
                    if img_url:
                        db.add(
                            MediaAsset(
                                post_id=post.id,
                                role='instagram',
                                public_url=img_url,
                                sort_order=sort_order,
                            )
                        )
                        sort_order += 1
            except Exception:
                pass

    # ---- Link to source content item and job ---------------------------- #
    if ci:
        post.content_item_id = ci.id
        post.job_id = ci.job_id
        post.ai_payload = {
            'caption': ci.instagram_caption,
            'hashtags': ci.instagram_hashtags,
            'blog_title': ci.blog_title,
            'blog_body': ci.blog_body,
            'blog_slug': ci.blog_slug,
        }

    await db.commit()
    await db.refresh(post)

    redirect_url = f'/admin/posts/{post.id}?msg=created'
    if source == 'job':
        redirect_url = f'/admin/posts/{post.id}?msg=created_from_job&job_id={job_id_raw}'
    return RedirectResponse(redirect_url, status_code=302)


# ----------------------------------------------------------------------- #
#  POST DETAIL                                                             #
# ----------------------------------------------------------------------- #

@router.get('/posts/{post_id}', response_class=HTMLResponse)
async def post_detail(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    post = await db.get(Post, post_id)
    if not post:
        return HTMLResponse('Not found', status_code=404)

    assets = (
        await db.execute(
            select(MediaAsset)
            .where(MediaAsset.post_id == post_id)
            .order_by(MediaAsset.role.asc(), MediaAsset.sort_order.asc())
        )
    ).scalars().all()

    instagram_assets = [a for a in assets if a.role == 'instagram']
    blog_assets = [a for a in assets if a.role == 'blog_cover']

    ai_payload_pretty = None
    if post.ai_payload:
        try:
            ai_payload_pretty = json.dumps(post.ai_payload, ensure_ascii=False, indent=2)
        except Exception:
            ai_payload_pretty = str(post.ai_payload)

    return templates.TemplateResponse(
        'post_detail.html',
        {
            'request': request,
            'post': post,
            'assets': assets,
            'instagram_assets': instagram_assets,
            'blog_assets': blog_assets,
            'ai_payload_pretty': ai_payload_pretty,
        },
    )


# ----------------------------------------------------------------------- #
#  POST EDIT                                                               #
# ----------------------------------------------------------------------- #

@router.get('/posts/{post_id}/edit', response_class=HTMLResponse)
async def post_edit_page(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    post = await db.get(Post, post_id)
    if not post:
        return HTMLResponse('Not found', status_code=404)
    return templates.TemplateResponse('post_edit.html', {'request': request, 'post': post})


@router.post('/posts/{post_id}/edit')
async def post_edit(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    post = await db.get(Post, post_id)
    if not post:
        return HTMLResponse('Not found', status_code=404)

    form = await request.form()

    blog_enabled = bool(form.get('blog_enabled')) if 'blog_enabled' in form else post.blog_enabled
    instagram_enabled = bool(form.get('instagram_enabled')) if 'instagram_enabled' in form else post.instagram_enabled

    post.topic = _clean_text(form, 'topic') or post.topic
    post.title = _clean_text(form, 'title') or post.title
    post.slug = _clean_text(form, 'slug') or post.slug
    post.poster = _clean_text(form, 'poster') or post.poster

    if blog_enabled:
        post.body_html = _clean_text(form, 'body_html')
        post.summary = _clean_text(form, 'summary')
        post.category = _clean_text(form, 'category')
        post.meta_title = _clean_text(form, 'meta_title')
        post.meta_description = _clean_text(form, 'meta_description')
        post.og_title = _clean_text(form, 'og_title')
        post.og_description = _clean_text(form, 'og_description')
        post.og_image = _clean_text(form, 'og_image')
        post.website_status = _normalize_website_status(_clean_text(form, 'website_status'))
        publish_date = _parse_publish_date(_clean_text(form, 'publish_date'))
        if publish_date:
            post.published_to_website_at = publish_date
    else:
        post.website_status = 'draft'

    if instagram_enabled:
        hashtags_raw = form.getlist('hashtags') if hasattr(form, 'getlist') else []
        post.instagram_caption = _clean_text(form, 'instagram_caption')
        post.hashtags = _normalize_hashtags(hashtags_raw, fallback=str(form.get('hashtags') or ''))
    else:
        post.instagram_caption = None
        post.hashtags = None
        post.instagram_status = 'not_published'

    post.blog_enabled = blog_enabled
    post.instagram_enabled = instagram_enabled

    await db.commit()
    await db.refresh(post)

    return RedirectResponse(f'/admin/posts/{post.id}?msg=updated', status_code=302)


@router.post('/posts/{post_id}/publish')
async def publish_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    await publish_post_to_website(post_id, db)
    return RedirectResponse(f'/admin/posts/{post_id}', status_code=302)


@router.post('/posts/{post_id}/unpublish')
async def unpublish_post_route(
    post_id: int,
    db: AsyncSession = Depends(get_current_admin),
    db_db: AsyncSession = Depends(get_db),
):
    await unpublish_post(post_id, db_db)
    return RedirectResponse(f'/admin/posts/{post_id}', status_code=302)


@router.delete('/posts/delete/{post_id}')
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    post = await db.get(Post, post_id)
    if not post:
        return JSONResponse(status_code=404, content={'detail': 'پست یافت نشد'})
    await db.delete(post)
    await db.commit()
    return JSONResponse(status_code=200, content={'detail': 'پست با موفقیت حذف شد'})
