from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.core.constants import PostWebsiteStatus


async def publish_post_to_website(post_id: int, db: AsyncSession) -> None:
    post = await db.get(Post, post_id)
    if not post:
        raise ValueError(f"Post {post_id} not found")
    post.website_status = PostWebsiteStatus.PUBLISHED
    post.published_to_website_at = datetime.now(timezone.utc)
    await db.commit()


async def unpublish_post(post_id: int, db: AsyncSession) -> None:
    post = await db.get(Post, post_id)
    if not post:
        raise ValueError(f"Post {post_id} not found")
    post.website_status = PostWebsiteStatus.DRAFT
    post.published_to_website_at = None
    await db.commit()
