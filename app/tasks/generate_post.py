import asyncio

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal

from app.services.post_service import PostService


@celery_app.task(bind=True)
def generate_post_task(
    self,
    topic: str,
    text_instruction: str,
    image_instruction: str,
    blog_image_count: int,
    instagram_image_count: int,
    auto_publish_blog: bool,
):

    async def run():

        async with AsyncSessionLocal() as db:

            service = PostService(db)

            post = await service.generate_post(
                topic=topic,
                text_instruction=text_instruction,
                image_instruction=image_instruction,
                blog_image_count=blog_image_count,
                instagram_image_count=instagram_image_count,
                auto_publish_blog=auto_publish_blog,
            )

            return post.id

    return asyncio.run(run())
