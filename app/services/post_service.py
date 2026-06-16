from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset

from app.services.ai_service import AIService
from app.services.image_service import download_image
from app.services.slug_service import slugify


class PostService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai = AIService(db)

    async def generate_post(
        self,
        topic: str,
        text_instruction: str,
        image_instruction: str,
        blog_image_count: int,
        instagram_image_count: int,
        auto_publish_blog: bool,
    ) -> Post:

        prompt = f"""
موضوع:
{topic}

دستور تولید متن:
{text_instruction}
"""

        ai_result = await self.ai.generate_text(prompt)

        slug = slugify(ai_result["slug"])

        post = Post(
            topic=topic,
            title=ai_result["title"],
            slug=slug,
            summary=ai_result["summary"],
            body_html=ai_result["body_html"],
            instagram_caption=ai_result["instagram_caption"],
            hashtags=ai_result["hashtags"],
            meta_title=ai_result["meta_title"],
            meta_description=ai_result["meta_description"],
            website_status="published" if auto_publish_blog else "draft",
            instagram_status="draft",
            source_type="ai",
            ai_payload=ai_result,
        )

        self.db.add(post)
        await self.db.flush()

        await self.generate_images(
            post,
            image_instruction,
            blog_image_count,
            instagram_image_count,
        )

        await self.db.commit()

        return post

    async def generate_images(
        self,
        post: Post,
        image_prompt: str,
        blog_count: int,
        insta_count: int,
    ):

        for i in range(blog_count):

            url = await self.ai.generate_image(
                f"{image_prompt} blog cover",
                size="1792x1024",
            )

            local_path, public_url = await download_image(url)

            asset = MediaAsset(
                post_id=post.id,
                role="blog",
                local_path=local_path,
                public_url=public_url,
                sort_order=i,
            )

            self.db.add(asset)

        for i in range(insta_count):

            url = await self.ai.generate_image(
                f"{image_prompt} instagram square",
                size="1024x1024",
            )

            local_path, public_url = await download_image(url)

            asset = MediaAsset(
                post_id=post.id,
                role="instagram",
                local_path=local_path,
                public_url=public_url,
                sort_order=i,
            )

            self.db.add(asset)
