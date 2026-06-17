# app/services/post_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging

from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.db.models.tag import Tag
from app.db.models.category import Category
from app.services.slug_service import slugify

logger = logging.getLogger(__name__)


class PostService:
    """Service for creating and managing posts (manual creation, no AI)"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_post(
        self,
        title: str,
        body_html: str,
        slug: Optional[str] = None,
        topic: Optional[str] = None,
        summary: Optional[str] = None,
        instagram_caption: Optional[str] = None,
        hashtags: Optional[str] = None,
        website_status: str = "draft",
        instagram_status: str = "draft",
        cover_image_url: Optional[str] = None,
        cover_image_file=None,  # UploadFile or None
        instagram_image_urls: Optional[List[str]] = None,
        instagram_image_files: Optional[List] = None,
        tag_names: Optional[List[str]] = None,
        category_names: Optional[List[str]] = None,
    ) -> Post:
        """
        Create a post manually (not AI-generated).

        Args:
            title: Post title (required)
            body_html: HTML body content (required)
            slug: URL slug (auto-generated if not provided)
            topic: Main topic/subject
            summary: Short summary
            instagram_caption: Instagram caption (optional)
            hashtags: Space-separated hashtags (optional)
            website_status: 'draft' or 'published'
            instagram_status: 'draft' or 'ready'
            cover_image_url: URL of cover image
            cover_image_file: Uploaded cover image file
            instagram_image_urls: List of Instagram image URLs
            instagram_image_files: List of uploaded Instagram image files
            tag_names: List of tag names to associate
            category_names: List of category names to associate
        """

        # Auto-generate slug if not provided
        if not slug:
            slug = slugify(title)

        # Ensure unique slug
        slug = await self._make_unique_slug(slug)

        # Create post
        post = Post(
            topic=topic or title,
            title=title,
            slug=slug,
            body_html=body_html,
            summary=summary or "",
            instagram_caption=instagram_caption or "",
            hashtags=hashtags or "",
            website_status=website_status,
            instagram_status=instagram_status,
            source_type="manual",  # ✅ Always manual for this service
            ai_prompt=None,        # ✅ No AI data
            ai_payload=None,       # ✅ No AI data
        )

        self.db.add(post)
        await self.db.flush()  # Get post.id before adding relations
        logger.info(f"📝 Manual post created with id={post.id}")

        # Handle cover image
        await self._add_cover_image(post, cover_image_url, cover_image_file)

        # Handle Instagram images
        await self._add_instagram_images(post, instagram_image_urls, instagram_image_files)

        # Handle tags
        if tag_names:
            await self._add_tags(post, tag_names)

        # Handle categories
        if category_names:
            await self._add_categories(post, category_names)

        await self.db.commit()
        await self.db.refresh(post)

        logger.info(f"✅ Post {post.id} created successfully with slug='{post.slug}'")
        return post

    async def _make_unique_slug(self, slug: str) -> str:
        """Ensure slug is unique by appending a number if needed"""
        base_slug = slug
        counter = 1

        while True:
            result = await self.db.execute(
                select(Post).where(Post.slug == slug)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                return slug

            slug = f"{base_slug}-{counter}"
            counter += 1

    async def _add_cover_image(
        self,
        post: Post,
        cover_image_url: Optional[str] = None,
        cover_image_file=None
    ):
        """Add cover image to post"""

        # Handle URL
        if cover_image_url:
            asset = MediaAsset(
                post_id=post.id,
                role="blog_cover",
                public_url=cover_image_url,
                sort_order=0,
            )
            self.db.add(asset)
            logger.info(f"   📸 Cover image added from URL")

        # Handle uploaded file (you'd need to save it first)
        elif cover_image_file:
            # TODO: Implement file saving logic
            # local_path = await save_uploaded_file(cover_image_file)
            # asset = MediaAsset(
            #     post_id=post.id,
            #     role="blog_cover",
            #     local_path=local_path,
            #     sort_order=0,
            # )
            # self.db.add(asset)
            pass

    async def _add_instagram_images(
        self,
        post: Post,
        image_urls: Optional[List[str]] = None,
        image_files: Optional[List] = None
    ):
        """Add Instagram images to post"""

        sort_order = 0

        # Handle URLs
        if image_urls:
            for url in image_urls:
                if url and url.strip():
                    asset = MediaAsset(
                        post_id=post.id,
                        role="instagram_image",
                        public_url=url.strip(),
                        sort_order=sort_order,
                    )
                    self.db.add(asset)
                    sort_order += 1
            logger.info(f"   📸 Added {sort_order} Instagram images from URLs")

        # Handle uploaded files
        if image_files:
            for file in image_files:
                if file and file.filename:
                    # TODO: Implement file saving logic
                    # local_path = await save_uploaded_file(file)
                    # asset = MediaAsset(
                    #     post_id=post.id,
                    #     role="instagram_image",
                    #     local_path=local_path,
                    #     sort_order=sort_order,
                    # )
                    # self.db.add(asset)
                    sort_order += 1

    async def _add_tags(self, post: Post, tag_names: List[str]):
        """Add tags to post (create if not exist)"""

        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if not tag_name:
                continue

            # Find or create tag
            result = await self.db.execute(
                select(Tag).where(Tag.name == tag_name)
            )
            tag = result.scalar_one_or_none()

            if not tag:
                tag = Tag(name=tag_name)
                self.db.add(tag)
                await self.db.flush()
                logger.info(f"   🏷️  Created new tag: {tag_name}")

            # Add to post if not already associated
            if tag not in post.tags:
                post.tags.append(tag)

    async def _add_categories(self, post: Post, category_names: List[str]):
        """Add categories to post (create if not exist)"""

        for cat_name in category_names:
            cat_name = cat_name.strip()
            if not cat_name:
                continue

            # Find or create category
            result = await self.db.execute(
                select(Category).where(Category.name == cat_name)
            )
            category = result.scalar_one_or_none()

            if not category:
                category = Category(name=cat_name)
                self.db.add(category)
                await self.db.flush()
                logger.info(f"   📁 Created new category: {cat_name}")

            # Add to post if not already associated
            if category not in post.categories:
                post.categories.append(category)
