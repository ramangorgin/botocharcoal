from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models.post import Post
from app.db.models.catalog import Catalog
from app.db.models.media_asset import MediaAsset
from app.core.constants import PostWebsiteStatus, MediaRole
from app.schemas.lead import LeadCreateSchema
from app.services.lead_service import create_lead

router = APIRouter()
templates = Jinja2Templates(directory="app/templates/public")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    catalogs = (await db.execute(
        select(Catalog).where(Catalog.is_active == True).limit(3)
    )).scalars().all()
    return templates.TemplateResponse("home.html", {"request": request, "catalogs": catalogs})


@router.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request, db: AsyncSession = Depends(get_db)):
    posts = (await db.execute(
        select(Post)
        .where(Post.website_status == PostWebsiteStatus.PUBLISHED)
        .order_by(Post.published_to_website_at.desc())
        .limit(20)
    )).scalars().all()
    return templates.TemplateResponse("blog_index.html", {"request": request, "posts": posts})


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_detail(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    post = (await db.execute(
        select(Post).where(Post.slug == slug, Post.website_status == PostWebsiteStatus.PUBLISHED)
    )).scalar_one_or_none()
    if not post:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    cover = (await db.execute(
        select(MediaAsset)
        .where(MediaAsset.post_id == post.id, MediaAsset.role == MediaRole.BLOG_COVER)
        .limit(1)
    )).scalar_one_or_none()
    return templates.TemplateResponse("blog_detail.html", {"request": request, "post": post, "cover": cover})


@router.get("/catalog", response_class=HTMLResponse)
async def catalog(request: Request, db: AsyncSession = Depends(get_db)):
    catalogs = (await db.execute(
        select(Catalog).where(Catalog.is_active == True)
    )).scalars().all()
    return templates.TemplateResponse("catalog.html", {"request": request, "catalogs": catalogs})


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
