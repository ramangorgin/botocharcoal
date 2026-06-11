from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.db.session import get_db
from app.db.models.post import Post
from app.db.models.catalog import Catalog
from app.db.models.media_asset import MediaAsset
from app.core.constants import PostWebsiteStatus, MediaRole
from app.schemas.lead import LeadCreateSchema
from app.services.lead_service import create_lead
from app.core.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates/public")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    catalogs = (await db.execute(
        select(Catalog).where(Catalog.is_active == True).limit(3)
    )).scalars().all()
    recent_posts_raw = (await db.execute(
        text("""SELECT id, topic, title, slug, body_html, instagram_caption, hashtags,
                       website_status, instagram_status, instagram_media_id,
                       published_to_website_at, published_to_instagram_at,
                       created_at, updated_at
                FROM posts
                WHERE website_status = 'published'
                ORDER BY published_to_website_at DESC
                LIMIT 3""")
    )).mappings().all()
    recent_posts = []
    for row in recent_posts_raw:
        post = Post(**dict(row))
        # Fetch cover for each post
        cover = (await db.execute(
            text("SELECT * FROM media_assets WHERE post_id = :post_id AND role = 'blog_cover' ORDER BY sort_order LIMIT 1"),
            {"post_id": post.id}
        )).mappings().one_or_none()
        post.cover = MediaAsset(**dict(cover)) if cover else None
        recent_posts.append(post)
    return templates.TemplateResponse("home.html", {"request": request, "catalogs": catalogs, "recent_posts": recent_posts})


@router.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request, db: AsyncSession = Depends(get_db)):
    posts_raw = (await db.execute(
        text("""SELECT id, topic, title, slug, body_html, instagram_caption, hashtags,
                       website_status, instagram_status, instagram_media_id,
                       published_to_website_at, published_to_instagram_at,
                       created_at, updated_at
                FROM posts
                WHERE website_status = 'published'
                ORDER BY published_to_website_at DESC
                LIMIT 20""")
    )).mappings().all()
    posts_with_covers = []
    for row in posts_raw:
        post = Post(**dict(row))
        cover_result = (await db.execute(
            select(MediaAsset)
            .where(MediaAsset.post_id == post.id, MediaAsset.role == MediaRole.BLOG_COVER)
            .limit(1)
        )).scalar_one_or_none()
        posts_with_covers.append({"post": post, "cover": cover_result})
    return templates.TemplateResponse("blog_index.html", {"request": request, "posts": posts_with_covers})


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_detail(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    post_raw = (await db.execute(
        text("SELECT * FROM posts WHERE slug = :slug AND website_status = 'published'"),
        {"slug": slug}
    )).mappings().one_or_none()
    if not post_raw:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    post = Post(**dict(post_raw))
    cover = (await db.execute(
        select(MediaAsset)
        .where(MediaAsset.post_id == post.id, MediaAsset.role == MediaRole.BLOG_COVER)
        .limit(1)
    )).scalar_one_or_none()
    # Fetch related posts (same topic, excluding current post)
    related_posts = []
    if post.topic:
        related_raw = (await db.execute(
            text("""SELECT id, topic, title, slug, body_html, instagram_caption, hashtags,
                           website_status, instagram_status, instagram_media_id,
                           published_to_website_at, published_to_instagram_at,
                           created_at, updated_at
                    FROM posts
                    WHERE id != :id AND website_status = 'published' AND topic = :topic
                    ORDER BY published_to_website_at DESC
                    LIMIT 3"""),
            {"id": post.id, "topic": post.topic}
        )).mappings().all()
        for row in related_raw:
            rp = Post(**dict(row))
            rcover = (await db.execute(
                select(MediaAsset)
                .where(MediaAsset.post_id == rp.id, MediaAsset.role == MediaRole.BLOG_COVER)
                .limit(1)
            )).scalar_one_or_none()
            related_posts.append({"post": rp, "cover": rcover})
    # Fallback: if no related by topic, get latest 3
    if not related_posts:
        latest_raw = (await db.execute(
            text("""SELECT id, topic, title, slug, body_html, instagram_caption, hashtags,
                           website_status, instagram_status, instagram_media_id,
                           published_to_website_at, published_to_instagram_at,
                           created_at, updated_at
                    FROM posts
                    WHERE id != :id AND website_status = 'published'
                    ORDER BY published_to_website_at DESC
                    LIMIT 3"""),
            {"id": post.id}
        )).mappings().all()
        for row in latest_raw:
            rp = Post(**dict(row))
            rcover = (await db.execute(
                select(MediaAsset)
                .where(MediaAsset.post_id == rp.id, MediaAsset.role == MediaRole.BLOG_COVER)
                .limit(1)
            )).scalar_one_or_none()
            related_posts.append({"post": rp, "cover": rcover})
    return templates.TemplateResponse("blog_detail.html", {
        "request": request,
        "post": post,
        "cover": cover,
        "related_posts": related_posts
    })


@router.get("/catalog", response_class=HTMLResponse)
async def catalog(request: Request, db: AsyncSession = Depends(get_db)):
    catalogs = (await db.execute(
        select(Catalog).where(Catalog.is_active == True)
    )).scalars().all()
    return templates.TemplateResponse("catalog.html", {"request": request, "catalogs": catalogs})


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


@router.post("/contact", response_class=HTMLResponse)
async def contact_submit(
    request: Request,
    name: str = Form(None),
    phone: str = Form(...),
    city: str = Form(None),
    message: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        schema = LeadCreateSchema(name=name, phone=phone, city=city, message=message)
        await create_lead(schema, db)
        return templates.TemplateResponse("contact.html", {"request": request, "success": True})
    except Exception as e:
        return templates.TemplateResponse("contact.html", {"request": request, "error": str(e)})


@router.get("/500", response_class=HTMLResponse)
async def error_500(request: Request):
    return templates.TemplateResponse("error_500.html", {"request": request}, status_code=500)


@router.get("/403", response_class=HTMLResponse)
async def error_403(request: Request):
    return templates.TemplateResponse("error_403.html", {"request": request}, status_code=403)
