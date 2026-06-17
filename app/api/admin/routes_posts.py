from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from fastapi.templating import Jinja2Templates

from app.db.session import get_db
from app.db.models import Post, Tag, Category
from app.api.admin.dependencies import get_current_admin

router = APIRouter()

# مسیر کلی template ها رو تعیین می‌کنیم
# این پوشه شامل زیرپوشه admin هم هست
from app.core.template_config import templates

@router.get("/posts")
async def posts_index(request: Request, db: AsyncSession = Depends(get_db), user=Depends(get_current_admin)):
    posts = await db.scalars(select(Post).order_by(Post.created_at.desc()))
    # حالا Jinja2 می‌تونه "admin/posts/index.html" رو پیدا کنه
    # چون "app/templates" روت اصلی هست و base.html هم در app/templates/base.html قرار داره
    return templates.TemplateResponse(
        "admin/posts/index.html",
        {"request": request, "posts": posts, "current_user": user}
    )


@router.get("/posts/create", response_class=HTMLResponse)
async def create_post_page(request: Request, db: AsyncSession = Depends(get_db), user=Depends(get_current_admin)):
    # اینجا هم مسیر فایل‌ها درست میشه
    return templates.TemplateResponse(
        "admin/posts/create.html",
        {"request": request, "current_user": user}
    )


@router.post("/posts/create")
async def create_post(
    request: Request,
    title: str = Form(...),
    slug: str = Form(...),
    content: str = Form(...),
    published: bool = Form(False),
    tags_input: str = Form(""), # Assuming tags are comma-separated
    categories_input: str = Form(""), # Assuming categories are comma-separated
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin)
):
    # Get all tags and categories to create new ones if they don't exist
    tag_names = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
    category_names = [cat.strip() for cat in categories_input.split(',') if cat.strip()]

    post = Post(
        title=title,
        slug=slug,
        content=content,
        published=published,
        author_id=user.id
    )
    db.add(post)
    await db.flush() # Flush to get the post object with its ID

    # Handle tags
    if tag_names:
        for tag_name in tag_names:
            tag = await db.scalar(select(Tag).where(Tag.name == tag_name))
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)
                await db.flush() # Flush to ensure tag has an ID if newly created
            post.tags.append(tag)

    # Handle categories
    if category_names:
        for category_name in category_names:
            category = await db.scalar(select(Category).where(Category.name == category_name))
            if not category:
                category = Category(name=category_name)
                db.add(category)
                await db.flush() # Flush to ensure category has an ID if newly created
            post.categories.append(category)

    await db.commit()

    # Redirect to the posts index page after creation
    response = RedirectResponse(url="/admin/posts", status_code=status.HTTP_303_SEE_OTHER)
    return response


@router.get("/posts/{post_id}/edit", response_class=HTMLResponse)
async def edit_post_page(request: Request, post_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_admin)):
    post = await db.scalar(select(Post).where(Post.id == post_id))
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Fetch all available tags and categories to populate dropdowns/selectors
    tags_query = await db.scalars(select(Tag))
    categories_query = await db.scalars(select(Category))

    # Convert tag and category objects to lists or sets for easier processing if needed
    all_tags = list(tags_query) if tags_query else []
    all_categories = list(categories_query) if categories_query else []

    # Get current tags and categories associated with the post
    current_tags = {tag.name for tag in post.tags}
    current_categories = {cat.name for cat in post.categories}

    return templates.TemplateResponse(
        "admin/posts/edit.html",
        {
            "request": request,
            "post": post,
            "current_user": user,
            "all_tags": all_tags,
            "all_categories": all_categories,
            "current_tags": current_tags,
            "current_categories": current_categories
        }
    )


@router.post("/posts/{post_id}/edit")
async def edit_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    slug: str = Form(...),
    content: str = Form(...),
    published: bool = Form(False),
    tags_input: str = Form(""),
    categories_input: str = Form(""),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin)
):
    post = await db.scalar(select(Post).where(Post.id == post_id))
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Update basic post fields
    post.title = title
    post.slug = slug
    post.content = content
    post.published = published

    # Handle tags
    tag_names = {tag.strip() for tag in tags_input.split(',') if tag.strip()}
    current_tag_names = {tag.name for tag in post.tags}

    # Add new tags
    for tag_name in tag_names - current_tag_names:
        tag = await db.scalar(select(Tag).where(Tag.name == tag_name))
        if not tag:
            tag = Tag(name=tag_name)
            db.add(tag)
            await db.flush() # Ensure tag has an ID if newly created
        post.tags.append(tag)

    # Remove old tags
    for tag_name in current_tag_names - tag_names:
        # Find the tag object to remove from the relationship
        tag_to_remove = next((tag for tag in post.tags if tag.name == tag_name), None)
        if tag_to_remove:
            post.tags.remove(tag_to_remove)

    # Handle categories (similar logic to tags)
    category_names = {cat.strip() for cat in categories_input.split(',') if cat.strip()}
    current_category_names = {cat.name for cat in post.categories}

    # Add new categories
    for category_name in category_names - current_category_names:
        category = await db.scalar(select(Category).where(Category.name == category_name))
        if not category:
            category = Category(name=category_name)
            db.add(category)
            await db.flush() # Ensure category has an ID if newly created
        post.categories.append(category)

    # Remove old categories
    for category_name in current_category_names - category_names:
        # Find the category object to remove from the relationship
        category_to_remove = next((cat for cat in post.categories if cat.name == category_name), None)
        if category_to_remove:
            post.categories.remove(category_to_remove)

    await db.commit()

    # Redirect to the edit page after update
    response = RedirectResponse(url=f"/admin/posts/{post_id}/edit", status_code=status.HTTP_303_SEE_OTHER)
    return response


@router.post("/posts/{post_id}/delete")
async def delete_post(request: Request, post_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_admin)):
    post = await db.scalar(select(Post).where(Post.id == post_id))
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Clear relationships before deleting the post to avoid foreign key issues
    # Important: Ensure Tag and Category models have cascade delete set appropriately or handle manually
    post.tags.clear()
    post.categories.clear()

    await db.delete(post)
    await db.commit()

    response = RedirectResponse(url="/admin/posts", status_code=status.HTTP_303_SEE_OTHER)
    return response



# In app/api/admin/routes_posts.py - Add this endpoint
@router.post("/posts/{post_id}/publish")
async def publish_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        return JSONResponse({"status": "error", "message": "Post not found"}, status_code=404)

    post.website_status = "published"
    post.published_to_website_at = func.now()
    await db.commit()

    return JSONResponse({"status": "success", "message": "Post published successfully"})
