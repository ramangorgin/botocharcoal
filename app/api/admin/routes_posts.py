# app/api/admin/routes_posts.py
from fastapi import APIRouter, Request, Depends, Form, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
import logging

from app.db.session import get_db
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.db.models.tag import Tag
from app.db.models.category import Category
from app.api.admin.dependencies import get_current_admin
from app.core.template_config import templates
from app.services.post_service import PostService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/posts", response_class=HTMLResponse)
async def list_posts(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),  # 'ai' or 'manual'
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    query = select(Post).order_by(desc(Post.created_at))

    if status:
        if status == "published":
            query = query.where(Post.website_status == "published")
        elif status == "draft":
            query = query.where(Post.website_status == "draft")

    if source:
        query = query.where(Post.source_type == source)

    # Get total count
    count_query = select(Post)
    if status:
        if status == "published":
            count_query = count_query.where(Post.website_status == "published")
        elif status == "draft":
            count_query = count_query.where(Post.website_status == "draft")
    if source:
        count_query = count_query.where(Post.source_type == source)

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
            "current_source": source,
        },
    )


@router.get("/posts/create", response_class=HTMLResponse)
async def create_post_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    """Show create post form"""

    # Get existing tags and categories for the form
    tags_result = await db.execute(select(Tag).order_by(Tag.name))
    tags = tags_result.scalars().all()

    categories_result = await db.execute(select(Category).order_by(Category.name))
    categories = categories_result.scalars().all()

    return templates.TemplateResponse(
        "admin/posts/create.html",
        {
            "request": request,
            "tags": tags,
            "categories": categories,
        },
    )


@router.post("/posts/create")
async def create_post(
    request: Request,
    title: str = Form(...),
    body_html: str = Form(""),
    slug: str = Form(""),
    topic: str = Form(""),
    summary: str = Form(""),
    instagram_caption: str = Form(""),
    hashtags: str = Form(""),
    website_status: str = Form("draft"),
    instagram_status: str = Form("draft"),
    cover_image_url: str = Form(""),
    cover_image_file: Optional[UploadFile] = File(None),
    ig_image_urls: str = Form(""),
    ig_image_files: Optional[List[UploadFile]] = File(None),
    tags_input: str = Form(""),  # Comma-separated or from select2
    categories_input: str = Form(""),  # Comma-separated or from select2
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    """Create a new post manually"""

    try:
        service = PostService(db)

        # Parse tags and categories from select2 input
        tag_names = [t.strip() for t in tags_input.split(',') if t.strip()] if tags_input else []
        category_names = [c.strip() for c in categories_input.split(',') if c.strip()] if categories_input else []

        # Parse Instagram image URLs
        ig_urls = [url.strip() for url in ig_image_urls.split('\n') if url.strip()] if ig_image_urls else []

        post = await service.create_post(
            title=title,
            body_html=body_html,
            slug=slug if slug else None,
            topic=topic if topic else title,
            summary=summary,
            instagram_caption=instagram_caption,
            hashtags=hashtags,
            website_status=website_status,
            instagram_status=instagram_status,
            cover_image_url=cover_image_url if cover_image_url else None,
            cover_image_file=cover_image_file,
            instagram_image_urls=ig_urls if ig_urls else None,
            instagram_image_files=ig_image_files,
            tag_names=tag_names if tag_names else None,
            category_names=category_names if category_names else None,
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({
                "status": "success",
                "message": "پست با موفقیت ایجاد شد",
                "redirect": f"/admin/posts/{post.id}"
            })

        return RedirectResponse(f"/admin/posts/{post.id}", status_code=303)

    except Exception as e:
        logger.error(f"❌ Failed to create post: {str(e)}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({
                "status": "error",
                "message": str(e)
            }, status_code=500)
        return RedirectResponse("/admin/posts?error=failed", status_code=303)


@router.get("/posts/{post_id}", response_class=HTMLResponse)
async def show_post(
    request: Request,
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(
            selectinload(Post.media_assets),
            selectinload(Post.tags),
            selectinload(Post.categories),
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=404
        )

    # Convert dates to Jalali
    import jdatetime

    def gregorian_to_jalali_str(dt):
        """Convert Gregorian datetime to Jalali string with Persian digits"""
        if not dt:
            return None

        jalali_date = jdatetime.datetime.fromgregorian(datetime=dt)

        persian_digits = {
            '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
            '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
        }

        date_str = jalali_date.strftime('%Y/%m/%d')
        time_str = jalali_date.strftime('%H:%M')

        for eng, per in persian_digits.items():
            date_str = date_str.replace(eng, per)
            time_str = time_str.replace(eng, per)

        return f"{date_str} {time_str}"

    post.jalali_created_at = gregorian_to_jalali_str(post.created_at)
    post.jalali_published_at = gregorian_to_jalali_str(post.published_to_website_at)

    return templates.TemplateResponse(
        "admin/posts/show.html",
        {
            "request": request,
            "post": post,
            "media_assets": post.media_assets,  # Already loaded via selectinload
        },
    )

@router.get("/posts/{post_id}/edit", response_class=HTMLResponse)
async def edit_post_form(
    request: Request,
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(
            selectinload(Post.tags),
            selectinload(Post.categories),
            selectinload(Post.media_assets),  # Eager load media_assets
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=404
        )

    # Get all tags and categories for the form
    tags_result = await db.execute(select(Tag).order_by(Tag.name))
    all_tags = tags_result.scalars().all()

    categories_result = await db.execute(select(Category).order_by(Category.name))
    all_categories = categories_result.scalars().all()

    return templates.TemplateResponse(
        "admin/posts/edit.html",
        {
            "request": request,
            "post": post,
            "all_tags": all_tags,
            "all_categories": all_categories,
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
    topic: str = Form(""),
    instagram_caption: str = Form(""),
    hashtags: str = Form(""),
    website_status: str = Form("draft"),
    instagram_status: str = Form("draft"),
    tags_input: str = Form(""),
    categories_input: str = Form(""),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(
            selectinload(Post.tags),
            selectinload(Post.categories),
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        return JSONResponse({"status": "error", "message": "Post not found"}, status_code=404)

    # Update basic fields
    post.title = title
    post.slug = slug
    post.topic = topic
    post.body_html = body_html
    post.summary = summary
    post.instagram_caption = instagram_caption
    post.hashtags = hashtags
    post.website_status = website_status
    post.instagram_status = instagram_status

    # Update tags
    if tags_input is not None:
        tag_names = [t.strip() for t in tags_input.split(',') if t.strip()]
        post.tags.clear()
        for tag_name in tag_names:
            result = await db.execute(select(Tag).where(Tag.name == tag_name))
            tag = result.scalar_one_or_none()
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)
            post.tags.append(tag)

    # Update categories
    if categories_input is not None:
        category_names = [c.strip() for c in categories_input.split(',') if c.strip()]
        post.categories.clear()
        for cat_name in category_names:
            result = await db.execute(select(Category).where(Category.name == cat_name))
            category = result.scalar_one_or_none()
            if not category:
                category = Category(name=cat_name)
                db.add(category)
            post.categories.append(category)

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
    """Publish a post to the blog"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        return JSONResponse(
            {"status": "error", "message": "Post not found"},
            status_code=404
        )

    try:
        post.website_status = "published"
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
    """Unpublish a post"""
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
    """Delete a post"""
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
