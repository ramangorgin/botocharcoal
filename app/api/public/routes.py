# app/api/public/routes.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging
from datetime import datetime
import jdatetime

from app.db.session import get_db
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.core.template_config import templates

logger = logging.getLogger(__name__)

# Define router FIRST before any decorators
router = APIRouter()


# Helper functions
def to_persian_digits(value):
    """Convert English digits to Persian"""
    if value is None:
        return ""
    persian_digits = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
    return str(value).translate(persian_digits)


def format_jalali_date(date_value):
    """Format date to Jalali with Persian digits"""
    if not date_value:
        return None

    if isinstance(date_value, str):
        try:
            date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        except:
            return None

    try:
        jalali = jdatetime.datetime.fromgregorian(datetime=date_value)
        months = [
            'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
        ]
        return f"{to_persian_digits(jalali.day)} {months[jalali.month - 1]} {to_persian_digits(jalali.year)}"
    except:
        return None


# Routes
@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Home page with recent posts"""
    query = (
        select(Post)
        .where(Post.website_status == "published")
        .options(selectinload(Post.media_assets))
        .order_by(Post.created_at.desc())
        .limit(6)
    )

    result = await db.execute(query)
    recent_posts = result.scalars().all()

    logger.info(f"📊 Home page: loaded {len(recent_posts)} recent posts")

    return templates.TemplateResponse(
        "public/home.html",
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

    # Check if post is published
    if post.website_status != "published":
        logger.warning(f"📊 Attempted to view unpublished post: {slug}")
        return templates.TemplateResponse(
            "public/errors/404.html",
            {"request": request},
            status_code=404
        )

    # Get images ordered
    images_query = (
        select(MediaAsset)
        .where(MediaAsset.post_id == post.id)
        .order_by(MediaAsset.sort_order)
    )
    images_result = await db.execute(images_query)
    images = images_result.scalars().all()

    # Find cover image
    cover = None
    for img in images:
        if img.role == "blog_cover":
            cover = img
            break

    # Format date
    post_persian_date = format_jalali_date(
        post.published_to_website_at or post.created_at
    )

    # Get related posts
    related_posts = []
    related_query = (
        select(Post)
        .where(
            Post.website_status == "published",
            Post.id != post.id,
        )
        .options(selectinload(Post.media_assets))
        .order_by(Post.created_at.desc())
        .limit(4)
    )
    related_result = await db.execute(related_query)
    related_posts_raw = related_result.scalars().all()

    # Format related posts with cover images
    for rp in related_posts_raw:
        rp_cover = None
        for img in rp.media_assets:
            if img.role == "blog_cover":
                rp_cover = img
                break

        related_posts.append({
            "post": rp,
            "cover": rp_cover,
            "persian_date": format_jalali_date(rp.created_at),
        })

    logger.info(f"📊 Blog post: {post.title}")

    return templates.TemplateResponse(
        "public/blog/show.html",
        {
            "request": request,
            "post": post,
            "images": images,
            "cover": cover,
            "post_persian_date": post_persian_date,
            "related_posts": related_posts,
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
