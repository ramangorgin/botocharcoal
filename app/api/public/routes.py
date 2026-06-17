# app/api/public/routes.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging

from app.db.session import get_db
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.core.template_config import templates  # Use shared templates

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Home page with recent posts"""

    # Eagerly load media_assets to avoid DetachedInstanceError
    query = (
        select(Post)
        .where(
            Post.website_status == "published"
        )
        .options(selectinload(Post.media_assets))
        .order_by(Post.created_at.desc())
        .limit(6)
    )

    result = await db.execute(query)
    recent_posts = result.scalars().all()

    logger.info(f"📊 Home page: loaded {len(recent_posts)} recent posts")

    return templates.TemplateResponse(
        "public/home.html",  # Note: full path from templates directory
        {
            "request": request,
            "recent_posts": recent_posts,
        }
    )


@router.get("/blog", response_class=HTMLResponse)
async def blog_index(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Blog listing page"""

    # Eagerly load media_assets
    query = (
        select(Post)
        .where(Post.website_status == "published")
        .options(selectinload(Post.media_assets))
        .order_by(Post.published_to_website_at.desc())
    )

    result = await db.execute(query)
    posts = result.scalars().all()

    logger.info(f"📊 Blog index: loaded {len(posts)} posts")

    return templates.TemplateResponse(
        "public/blog/index.html",
        {
            "request": request,
            "posts": posts,
        }
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_detail(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Single blog post page"""

    # Eagerly load relationships
    query = (
        select(Post)
        .where(Post.slug == slug)
        .options(
            selectinload(Post.media_assets),
            selectinload(Post.tags),
            selectinload(Post.categories),
        )
    )

    result = await db.execute(query)
    post = result.scalar_one_or_none()

    if not post:
        logger.warning(f"📊 Blog post not found: {slug}")
        return templates.TemplateResponse(
            "public/errors/404.html",
            {"request": request},
            status_code=404
        )

    # Get images separately (ordered)
    images_query = (
        select(MediaAsset)
        .where(MediaAsset.post_id == post.id)
        .order_by(MediaAsset.sort_order)
    )
    images_result = await db.execute(images_query)
    images = images_result.scalars().all()

    logger.info(f"📊 Blog post: {post.title}")

    return templates.TemplateResponse(
        "public/blog/show.html",
        {
            "request": request,
            "post": post,
            "images": images,
        }
    )


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """About page"""
    return templates.TemplateResponse(
        "public/about.html",
        {"request": request},
    )


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    """Contact page"""
    return templates.TemplateResponse(
        "public/contact.html",
        {"request": request},
    )
