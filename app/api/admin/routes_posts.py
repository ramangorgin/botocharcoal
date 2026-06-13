import jdatetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.api.deps import get_current_admin
from app.services.website_publish import publish_post_to_website, unpublish_post
from app.core.constants import PostWebsiteStatus, PostInstagramStatus

router = APIRouter()
templates = Jinja2Templates(directory="app/templates/admin")


def format_jalali_date(dt):
    """Convert datetime to Jalali date string (YYYY/MM/DD with Persian numbers)."""
    if not dt:
        return '-'
    jdt = jdatetime.datetime.fromgregorian(datetime=dt)
    jalali_str = jdt.strftime('%Y/%m/%d')
    # Convert to Persian numbers
    persian_digits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']
    result = ''
    for d in jalali_str:
        if d.isdigit():
            result += persian_digits[int(d)]
        else:
            result += d
    return result


@router.get("/posts", response_class=HTMLResponse)
async def posts_list(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    posts = (await db.execute(select(Post).order_by(Post.created_at.desc()))).scalars().all()
    # Add Jalali date to each post
    for post in posts:
        if post.created_at:
            jdt = jdatetime.datetime.fromgregorian(datetime=post.created_at)
            jalali_str = jdt.strftime('%Y/%m/%d')
            persian_digits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']
            post.jalali_date = ''.join(persian_digits[int(d)] if d.isdigit() else d for d in jalali_str)
        else:
            post.jalali_date = '-'
    return templates.TemplateResponse("posts_list.html", {"request": request, "posts": posts})


@router.get("/posts/create", response_class=HTMLResponse)
async def post_create_page(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    return templates.TemplateResponse("post_create.html", {"request": request, "post": None})


@router.post("/posts/create", response_class=HTMLResponse)
async def post_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    form = await request.form()
    title = form.get("title", "").strip()
    slug = form.get("slug", "").strip()
    topic = form.get("topic", "").strip()
    body_html = form.get("body_html", "")
    instagram_caption = form.get("instagram_caption", "")
    hashtags = form.get("hashtags", "")
    meta_title = form.get("meta_title", "").strip()
    meta_description = form.get("meta_description", "").strip()
    og_title = form.get("og_title", "").strip()
    og_description = form.get("og_description", "")
    og_image = form.get("og_image", "").strip()
    website_status = form.get("website_status", "DRAFT")
    publish_date = form.get("publish_date", "").strip()
    
    post = Post(
        title=title,
        slug=slug,
        topic=topic,
        body_html=body_html,
        instagram_caption=instagram_caption,
        hashtags=hashtags,
        meta_title=meta_title or None,
        meta_description=meta_description or None,
        og_title=og_title or None,
        og_description=og_description or None,
        og_image=og_image or None,
        website_status=website_status,
    )
    if publish_date:
        from datetime import datetime as dt
        try:
            post.published_to_website_at = dt.fromisoformat(publish_date)
        except Exception:
            pass
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return RedirectResponse(f"/admin/posts/{post.id}?msg=created", status_code=302)


@router.get("/posts/{post_id}/edit", response_class=HTMLResponse)
async def post_edit_page(post_id: int, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    post = await db.get(Post, post_id)
    if not post:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse("post_edit.html", {"request": request, "post": post})


@router.post("/posts/{post_id}/edit", response_class=HTMLResponse)
async def post_edit(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    post = await db.get(Post, post_id)
    if not post:
        return HTMLResponse("Not found", status_code=404)
    
    form = await request.form()
    title = form.get("title", "").strip()
    slug = form.get("slug", "").strip()
    topic = form.get("topic", "").strip()
    body_html = form.get("body_html", "")
    instagram_caption = form.get("instagram_caption", "")
    hashtags_raw = form.get("hashtags", "")
    meta_title = form.get("meta_title", "").strip()
    meta_description = form.get("meta_description", "").strip()
    og_title = form.get("og_title", "").strip()
    og_description = form.get("og_description", "")
    og_image = form.get("og_image", "").strip()
    website_status = form.get("website_status", "DRAFT")
    
    publish_date = form.get("publish_date", "").strip()
    if publish_date:
        from datetime import datetime as dt
        try:
            post.published_to_website_at = dt.fromisoformat(publish_date)
        except Exception:
            pass
    
    post.title = title
    post.slug = slug
    post.topic = topic
    post.body_html = body_html
    post.instagram_caption = instagram_caption
    post.hashtags = hashtags_raw
    post.meta_title = meta_title or None
    post.meta_description = meta_description or None
    post.og_title = og_title or None
    post.og_description = og_description or None
    post.og_image = og_image or None
    post.website_status = website_status
    
    await db.commit()
    await db.refresh(post)
    return RedirectResponse(f"/admin/posts/{post.id}?msg=updated", status_code=302)


@router.get("/posts/{post_id}", response_class=HTMLResponse)
async def post_detail(post_id: int, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    post = await db.get(Post, post_id)
    if not post:
        return HTMLResponse("Not found", status_code=404)
    assets = (await db.execute(
        select(MediaAsset).where(MediaAsset.post_id == post_id).order_by(MediaAsset.sort_order)
    )).scalars().all()
    return templates.TemplateResponse("post_detail.html", {"request": request, "post": post, "assets": assets})


@router.post("/posts/{post_id}/publish")
async def publish_post(post_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    await publish_post_to_website(post_id, db)
    return RedirectResponse(f"/admin/posts/{post_id}", status_code=302)


@router.post("/posts/{post_id}/unpublish")
async def unpublish(post_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    await unpublish_post(post_id, db)
    return RedirectResponse(f"/admin/posts/{post_id}", status_code=302)


@router.delete("/posts/delete/{post_id}")
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    post = await db.get(Post, post_id)
    if not post:
        return JSONResponse(status_code=404, content={"detail": "نوشته‌ای یافت نشد"})
    await db.delete(post)
    await db.commit()
    return JSONResponse(status_code=200, content={"detail": "نوشته با موفقیت حذف شد"})
