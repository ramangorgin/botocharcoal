"""
Botocharcoal — AI Content Pipeline Celery Task
================================================
Generates Persian blog posts, Instagram captions, and images
for a given Job. Saves results to ContentItem records.
"""

import asyncio
import json
from datetime import datetime, timezone
from celery import shared_task
from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.core.constants import JobStatus, MediaRole
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.db.models.job import Job
from app.db.models.content_item import ContentItem
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.services.ai_text import (
    generate_blog_text,
    generate_instagram_caption,
    generate_instagram_hashtags,
    generate_image_prompt,
)
from app.services.ai_image import generate_image, generate_and_save_images
from app.core.constants import INSTAGRAM_IMAGE_SIZE, BLOG_COVER_SIZE
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
                # Load content items for this job
                from sqlalchemy import select
                result = await db.execute(
                    select(ContentItem).where(
                        ContentItem.job_id == job_id
                    ).order_by(ContentItem.day_number, ContentItem.id)
                )
                content_items = result.scalars().all()
                if not content_items:
                    raise ValueError(f"Content items not found for job {job_id}")

                # Process each day
                for idx, ci in enumerate(content_items):
                    day_num = ci.day_number
                    logger.info("pipeline_day_start", job_id=job_id, day=day_num)

                    ci.status = JobStatus.PROCESSING
                    await db.commit()

                    # 1. Generate blog title/body
                    logger.info("pipeline_generate_blog", job_id=job_id, day=day_num)
                    blog_data = await generate_blog_text(
                        subject=job.subject,
                        instructions=job.instructions or "",
                    )
                    blog_title = blog_data.get("title", job.subject)
                    blog_slug = blog_data.get("slug", slugify(blog_title))
                    blog_body = blog_data.get("body_html", "")

                    # 2. Generate Instagram content
                    logger.info("pipeline_generate_instagram", job_id=job_id, day=day_num)
                    caption = await generate_instagram_caption(
                        subject=job.subject,
                        instructions=job.instructions or "",
                    )
                    hashtags = await generate_instagram_hashtags(
                        subject=job.subject,
                        instructions=job.instructions or "",
                    )

                    # 3. Generate image prompts
                    logger.info("pipeline_generate_image_prompts", job_id=job_id, day=day_num)
                    ig_prompts = []
                    for i in range(job.instagram_image_count):
                        prompt = await generate_image_prompt(
                            subject=job.subject,
                            instructions=job.instructions or "",
                        )
                        ig_prompts.append(prompt)

                    blog_prompts = []
                    for i in range(job.blog_image_count):
                        prompt = await generate_image_prompt(
                            subject=job.subject,
                            instructions=job.instructions or "",
                        )
                        blog_prompts.append(prompt)

                    # 4. Generate Instagram images
                    logger.info("pipeline_generate_ig_images", job_id=job_id, day=day_num, count=len(ig_prompts))
                    ig_assets = await generate_and_save_images(
                        prompts=ig_prompts,
                        job_id=job_id,
                        role="instagram",
                    )

                    # 5. Generate blog images
                    logger.info("pipeline_generate_blog_images", job_id=job_id, day=day_num, count=len(blog_prompts))
                    blog_assets = await generate_and_save_images(
                        prompts=blog_prompts,
                        job_id=job_id,
                        role="blog_cover",
                    )

                    # Save results to ContentItem
                    ig_image_urls = json.dumps([a["public_url"] for a in ig_assets])
                    blog_image_urls = json.dumps([a["public_url"] for a in blog_assets])
                    ai_response = json.dumps({
                        "blog": blog_data,
                        "caption_length": len(caption),
                        "hashtag_count": len(hashtags.split()),
                        "ig_image_count": len(ig_assets),
                        "blog_image_count": len(blog_assets),
                    })

                    ci.blog_title = blog_title
                    ci.blog_slug = blog_slug
                    ci.blog_body = blog_body
                    ci.instagram_caption = caption
                    ci.instagram_hashtags = hashtags
                    ci.instagram_image_urls = ig_image_urls
                    ci.blog_image_urls = blog_image_urls
                    ci.ai_response = ai_response
                    ci.status = JobStatus.COMPLETED

                    await db.commit()

                    # 6. Auto-publish blog if enabled
                    if job.auto_publish_blog:
                        logger.info("pipeline_auto_publish_blog", job_id=job_id, day=day_num)
                        try:
                            existing = await db.execute(
                                select(Post).where(Post.slug == blog_slug)
                            )
                            if not existing.scalars().first():
                                post = Post(
                                    topic=job.subject,
                                    title=blog_title,
                                    slug=blog_slug,
                                    body_html=blog_body,
                                    instagram_caption=caption,
                                    hashtags=hashtags,
                                    website_status="published",
                                )
                                db.add(post)
                                await db.flush()

                                post_id = post.id
                                for a in ig_assets:
                                    db.add(MediaAsset(
                                        post_id=post_id,
                                        job_id=job_id,
                                        role=MediaRole.INSTAGRAM,
                                        prompt=a["prompt"],
                                        local_path=a["local_path"],
                                        public_url=a["public_url"],
                                        sort_order=a["sort_order"],
                                    ))
                                for a in blog_assets:
                                    db.add(MediaAsset(
                                        post_id=post_id,
                                        job_id=job_id,
                                        role=MediaRole.BLOG_COVER,
                                        prompt=a["prompt"],
                                        local_path=a["local_path"],
                                        public_url=a["public_url"],
                                        sort_order=0,
                                    ))
                                await db.commit()
                                logger.info("blog_post_created", post_id=post_id, blog_slug=blog_slug)
                            else:
                                logger.info("blog_already_exists", blog_slug=blog_slug)
                        except Exception as post_exc:
                            logger.warning("auto_publish_failed", job_id=job_id, day=day_num, error=str(post_exc))

                # Mark job complete
                job.blog_title = f"{job.subject} (AI Generated)"
                job.status = JobStatus.COMPLETED
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()

                logger.info("pipeline_completed", job_id=job_id, items_generated=len(content_items))
                return {"job_id": job_id, "items_generated": len(content_items)}

            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                job.retry_count += 1
                await db.commit()
                logger.error("pipeline_failed", job_id=job_id, error=str(exc))
                raise self.retry(exc=exc)

    return _run(_pipeline())
