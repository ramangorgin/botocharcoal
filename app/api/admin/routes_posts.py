# app/api/admin/routes_posts.py
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional
import logging

from app.db.session import get_db
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.api.admin.dependencies import get_current_admin
from app.core.template_config import templates

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/posts", response_class=HTMLResponse)
async def list_posts(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    query = select(Post).order_by(desc(Post.created_at))

    if status:
        if status == "published":
            query = query.where(Post.website_status == "published")
        elif status == "draft":
            query = query.where(Post.website_status == "draft")

    # Get total count
    count_query = select(Post)
    if status:
        if status == "published":
            count_query = count_query.where(Post.website_status == "published")
        elif status == "draft":
            count_query = count_query.where(Post.website_status == "draft")

    result = await db.execute(count_query)
    total = result.scalars().all()
    total_count = len(total)

    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    posts = result.scalars().all()

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    return templates.TemplateResponse(
        "admin/posts/index.html",
        {
            "request": request,
            "posts": posts,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_count": total_count,
            "current_status": status,
        },
    )


@router.get("/posts/{post_id}", response_class=HTMLResponse)
async def show_post(
    request: Request,
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=404
        )

    # Get media assets
    assets_result = await db.execute(
        select(MediaAsset).where(MediaAsset.post_id == post.id).order_by(MediaAsset.sort_order)
    )
    media_assets = assets_result.scalars().all()

    return templates.TemplateResponse(
        "admin/posts/show.html",
        {
            "request": request,
            "post": post,
            "media_assets": media_assets,
        },
    )


@router.get("/posts/{post_id}/edit", response_class=HTMLResponse)
async def edit_post_form(
    request: Request,
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=404
        )

    return templates.TemplateResponse(
        "admin/posts/edit.html",
        {
            "request": request,
            "post": post,
        },
    )


@router.post("/posts/{post_id}/edit")
async def update_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    slug: str = Form(...),
    body_html: str = Form(""),
    summary: str = Form(""),
    instagram_caption: str = Form(""),
    hashtags: str = Form(""),
    meta_title: str = Form(""),
    meta_description: str = Form(""),
    website_status: str = Form("draft"),
    instagram_status: str = Form("draft"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        return JSONResponse({"status": "error", "message": "Post not found"}, status_code=404)

    # Update fields
    post.title = title
    post.slug = slug
    post.body_html = body_html
    post.summary = summary
    post.instagram_caption = instagram_caption
    post.hashtags = hashtags
    post.meta_title = meta_title
    post.meta_description = meta_description
    post.website_status = website_status
    post.instagram_status = instagram_status

    await db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Post updated successfully"})

    return RedirectResponse(f"/admin/posts/{post.id}", status_code=303)


@router.post("/posts/{post_id}/publish")
async def publish_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    """
    Publish a post to the blog (set website_status to 'published')
    """
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        return JSONResponse(
            {"status": "error", "message": "Post not found"},
            status_code=404
        )

    try:
        # Update post status
        post.website_status = "published"

        # Set published date if not already set
        if not post.published_to_website_at:
            post.published_to_website_at = func.now()

        await db.commit()

        logger.info(f"✅ Post {post_id} published successfully")

        return JSONResponse({
            "status": "success",
            "message": "پست با موفقیت در بلاگ منتشر شد",
            "post_id": post.id,
            "slug": post.slug
        })

    except Exception as e:
        logger.error(f"❌ Failed to publish post {post_id}: {str(e)}")
        return JSONResponse(
            {"status": "error", "message": f"خطا در انتشار پست: {str(e)}"},
            status_code=500
        )


@router.post("/posts/{post_id}/unpublish")
async def unpublish_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    """
    Unpublish a post (set website_status back to 'draft')
    """
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        return JSONResponse(
            {"status": "error", "message": "Post not found"},
            status_code=404
        )

    try:
        post.website_status = "draft"
        await db.commit()

        logger.info(f"✅ Post {post_id} unpublished")

        return JSONResponse({
            "status": "success",
            "message": "پست از حالت انتشار خارج شد"
        })

    except Exception as e:
        logger.error(f"❌ Failed to unpublish post {post_id}: {str(e)}")
        return JSONResponse(
            {"status": "error", "message": f"خطا: {str(e)}"},
            status_code=500
        )


@router.post("/posts/{post_id}/delete")
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    """
    Delete a post
    """
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        return JSONResponse(
            {"status": "error", "message": "Post not found"},
            status_code=404
        )

    try:
        await db.delete(post)
        await db.commit()

        logger.info(f"✅ Post {post_id} deleted")

        return JSONResponse({
            "status": "success",
            "message": "پست با موفقیت حذف شد"
        })

    except Exception as e:
        logger.error(f"❌ Failed to delete post {post_id}: {str(e)}")
        return JSONResponse(
            {"status": "error", "message": f"خطا در حذف پست: {str(e)}"},
            status_code=500
        )
