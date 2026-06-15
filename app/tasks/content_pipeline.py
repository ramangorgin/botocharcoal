"""
Botocharcoal — AI Content Pipeline Celery Task
==============================================
Generates one full post row per content item and stores it in posts table.
"""

import asyncio
import json
from datetime import datetime, timezone
from celery import Celery
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models.job import Job
from app.db.models.content_item import ContentItem
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.services.ai_text import generate_post_row, generate_image_prompt
from app.services.ai_image import generate_and_save_images
from app.tasks.celery_app import celery_app
from app.core.constants import JobStatus
from app.core.logging import logger


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="tasks.run_content_pipeline")
def run_content_pipeline(self, job_id: int) -> dict:
    async def _pipeline():
        async with AsyncSessionLocal() as db:
            job: Job | None = await db.get(Job, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

            try:
                result = await db.execute(
                    select(ContentItem)
                    .where(ContentItem.job_id == job_id)
                    .order_by(ContentItem.day_number, ContentItem.id)
                )
                content_items = result.scalars().all()
                if not content_items:
                    raise ValueError(f"No content items for job {job_id}")

                for ci in content_items:
                    ci.status = JobStatus.PROCESSING
                    await db.commit()

                    row = await generate_post_row(
                        subject=job.subject,
                        instructions=job.instructions or "",
                    )

                    if not row.get("topic"):
                        row["topic"] = job.subject

                    if not row.get("slug"):
                        row["slug"] = f"job-{job.id}-item-{ci.id}"

                    existing = await db.execute(select(Post).where(Post.slug == row["slug"]))
                    if existing.scalars().first():
                        row["slug"] = f"{row['slug']}-{ci.id}"

                    post = Post(
                        topic=row.get("topic") or job.subject,
                        title=row.get("title") or job.subject,
                        slug=row["slug"],
                        body_html=row.get("body_html"),
                        summary=row.get("summary"),
                        category=row.get("category"),
                        cover_image_url=row.get("cover_image_url"),
                        instagram_caption=row.get("instagram_caption"),
                        hashtags=row.get("hashtags"),
                        website_status="draft",
                        instagram_status="not_published",
                        meta_title=row.get("meta_title"),
                        meta_description=row.get("meta_description"),
                        og_title=row.get("og_title"),
                        og_description=row.get("og_description"),
                        og_image=row.get("og_image"),
                        source_type="ai",
                        blog_enabled=bool(row.get("blog_enabled", True)),
                        instagram_enabled=bool(row.get("instagram_enabled", True)),
                        ai_payload=row,
                        job_id=job.id,
                        content_item_id=ci.id,
                    )
                    db.add(post)
                    await db.flush()

                    ig_assets: list[dict] = []
                    blog_assets: list[dict] = []

                    prompt = await generate_image_prompt(
                        subject=job.subject,
                        instructions=job.instructions or "",
                    )

                    if post.instagram_enabled and job.instagram_image_count > 0:
                        ig_assets = await generate_and_save_images(
                            prompts=[prompt] * job.instagram_image_count,
                            job_id=job.id,
                            role="instagram",
                        )
                        for asset in ig_assets:
                            db.add(
                                MediaAsset(
                                    post_id=post.id,
                                    job_id=job.id,
                                    role="instagram",
                                    prompt=asset.get("prompt"),
                                    local_path=asset.get("local_path"),
                                    public_url=asset.get("public_url"),
                                    sort_order=asset.get("sort_order", 0),
                                )
                            )

                    if post.blog_enabled and job.blog_image_count > 0:
                        blog_assets = await generate_and_save_images(
                            prompts=[prompt] * job.blog_image_count,
                            job_id=job.id,
                            role="blog_cover",
                        )
                        for idx, asset in enumerate(blog_assets):
                            db.add(
                                MediaAsset(
                                    post_id=post.id,
                                    job_id=job.id,
                                    role="blog_cover",
                                    prompt=asset.get("prompt"),
                                    local_path=asset.get("local_path"),
                                    public_url=asset.get("public_url"),
                                    sort_order=idx,
                                )
                            )
                        if blog_assets and not post.cover_image_url:
                            post.cover_image_url = blog_assets[0].get("public_url")

                    ci.blog_title = post.title if post.blog_enabled else None
                    ci.blog_slug = post.slug if post.blog_enabled else None
                    ci.blog_body = post.body_html if post.blog_enabled else None
                    ci.blog_image_urls = json.dumps([a.get("public_url") for a in blog_assets]) if blog_assets else None
                    ci.instagram_caption = post.instagram_caption if post.instagram_enabled else None
                    ci.instagram_hashtags = post.hashtags if post.instagram_enabled else None
                    ci.instagram_image_urls = json.dumps([a.get("public_url") for a in ig_assets]) if ig_assets else None
                    ci.ai_response = json.dumps(row, ensure_ascii=False)
                    ci.status = JobStatus.COMPLETED

                    if job.auto_publish_blog and post.blog_enabled:
                        post.website_status = "published"
                        post.published_to_website_at = datetime.now(timezone.utc)

                    await db.commit()

                job.status = JobStatus.COMPLETED
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()

                return {"job_id": job_id, "items_generated": len(content_items)}

            except Exception as exc:
                logger.exception("content_pipeline_failed", job_id=job_id, error=str(exc))
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                job.retry_count = (job.retry_count or 0) + 1
                await db.commit()
                raise self.retry(exc=exc)

    return _run(_pipeline())
