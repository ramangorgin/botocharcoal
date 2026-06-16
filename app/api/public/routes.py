from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.templating import Jinja2Templates
from app.core.config import settings

from app.db.session import get_db, AsyncSessionLocal
from app.db.models import Post, MediaAsset

router = APIRouter()

templates = Jinja2Templates(directory="app/templates/public")


@router.get("/")
async def home(request: Request):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Post)
            .where(
                Post.blog_enabled == True,
                Post.website_status == "published"
            )
            .order_by(Post.created_at.desc())
            .limit(6)
        )
        recent_posts = result.scalars().all()

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "recent_posts": recent_posts,
        }
    )


@router.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Post)
        .where(Post.website_status == "published")
        .order_by(Post.published_to_website_at.desc())
    )

    posts = result.scalars().all()

    return templates.TemplateResponse(
        "blog/index.html",
        {
            "request": request,
            "posts": posts,
        },
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_detail(slug: str, request: Request, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Post).where(Post.slug == slug)
    )

    post = result.scalar_one_or_none()

    if not post:
        return templates.TemplateResponse(
            "404.html",
            {"request": request},
            status_code=404,
        )

    media = await db.execute(
        select(MediaAsset)
        .where(MediaAsset.post_id == post.id)
        .order_by(MediaAsset.sort_order)
    )

    images = media.scalars().all()

    return templates.TemplateResponse(
        "blog/show.html",
        {
            "request": request,
            "post": post,
            "images": images,
        },
    )


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):

    return templates.TemplateResponse(
        "about.html",
        {"request": request},
    )


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):

    return templates.TemplateResponse(
        "contact.html",
        {"request": request},
    )
