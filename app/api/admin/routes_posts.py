from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.api.deps import get_current_admin
from app.services.website_publish import publish_post_to_website, unpublish_post

router = APIRouter()
templates = Jinja2Templates(directory="app/templates/admin")


@router.get("/posts", response_class=HTMLResponse)
async def posts_list(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    posts = (await db.execute(select(Post).order_by(Post.created_at.desc()))).scalars().all()
    return templates.TemplateResponse("posts_list.html", {"request": request, "posts": posts})


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
