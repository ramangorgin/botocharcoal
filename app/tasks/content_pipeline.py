import asyncio
from datetime import datetime, timezone
from celery import shared_task
from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.core.constants import JobStatus, MediaRole
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.db.models.job import Job
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.services.ai_text import generate_text_pack
from app.services.ai_image import generate_and_save_images
from app.services.instagram import publish_carousel
from slugify import slugify


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="tasks.run_content_pipeline")
def run_content_pipeline(self, job_id: int) -> dict:
    async def _pipeline():
        async with AsyncSessionLocal() as db:
            job: Job = await db.get(Job, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

            try:
                # 1. Generate text
                logger.info("pipeline_text_start", job_id=job_id)
                pack = await generate_text_pack(
                    topic=job.topic,
                    tone=job.tone,
                    cta_text=job.cta_text,
                    image_count=job.image_count,
                )

                job.generated_blog_title = pack["blog_title"]
                job.generated_blog_slug = pack.get("blog_slug") or slugify(pack["blog_title"])
                job.generated_blog_body = pack["blog_body"]
                job.generated_caption = pack["instagram_caption"]
                job.generated_hashtags = pack["hashtags"]
                job.generated_image_prompts = "\n---\n".join(pack["image_prompts"])
                await db.commit()

                # 2. Generate Instagram images
                logger.info("pipeline_images_start", job_id=job_id)
                ig_assets = await generate_and_save_images(
                    prompts=pack["image_prompts"],
                    job_id=job_id,
                    role="instagram",
                    media_root=settings.MEDIA_ROOT,
                    base_url=settings.BASE_URL,
                )

                # 3. Generate blog cover
                cover_assets = await generate_and_save_images(
                    prompts=[pack["blog_cover_prompt"]],
                    job_id=job_id,
                    role="blog_cover",
                    media_root=settings.MEDIA_ROOT,
                    base_url=settings.BASE_URL,
                )

                # 4. Create Post record
                post = Post(
                    topic=job.topic,
                    title=pack["blog_title"],
                    slug=job.generated_blog_slug,
                    body_html=pack["blog_body"],
                    instagram_caption=pack["instagram_caption"],
                    hashtags=pack["hashtags"],
                )
                db.add(post)
                await db.flush()  # get post.id

                # 5. Save MediaAssets
                for a in ig_assets:
                    db.add(MediaAsset(
                        post_id=post.id, job_id=job_id,
                        role=MediaRole.INSTAGRAM,
                        prompt=a["prompt"],
                        local_path=a["local_path"],
                        public_url=a["public_url"],
                        sort_order=a["sort_order"],
                    ))
                for a in cover_assets:
                    db.add(MediaAsset(
                        post_id=post.id, job_id=job_id,
                        role=MediaRole.BLOG_COVER,
                        prompt=a["prompt"],
                        local_path=a["local_path"],
                        public_url=a["public_url"],
                        sort_order=0,
                    ))

                # 6. Publish to Instagram
                caption_full = f"{pack['instagram_caption']}\n.\n.\n.\n{pack['hashtags']}"
                ig_media_id = await publish_carousel(
                    image_urls=[a["public_url"] for a in ig_assets],
                    caption=caption_full,
                )
                post.instagram_status = PostInstagramStatus.PUBLISHED
                post.instagram_media_id = ig_media_id
                post.published_to_instagram_at = datetime.now(timezone.utc)

                job.status = JobStatus.COMPLETED
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info("pipeline_completed", job_id=job_id, post_id=post.id)
                return {"job_id": job_id, "post_id": post.id}

            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                job.retry_count += 1
                await db.commit()
                logger.error("pipeline_failed", job_id=job_id, error=str(exc))
                raise self.retry(exc=exc)

    return _run(_pipeline())
