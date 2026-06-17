# app/tasks/generate_post.py
import asyncio
import json
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session
from app.db.models.job import Job
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.services.ai_service import generate_content_with_ai, generate_images_with_ai

# Import celery app
from app.tasks.celery_app import celery_app


def _run_async(coro):
    """اجرای کد async در محیط synchronous"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_job_task(self, job_id: int):
    """
    تسک Celery برای پردازش Job
    """
    # این تابع sync است اما داخلش async فراخوانی می‌کنیم

    async def _process_async():
        async with async_session() as db:
            try:
                # دریافت Job
                result = await db.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job:
                    return {"error": f"Job with id {job_id} not found"}

                # به‌روزرسانی وضعیت به processing
                job.status = "processing"
                await db.commit()

                # ۱. تولید محتوای متنی
                text_result = await generate_content_with_ai(
                    topic=job.topic,
                    instructions=job.text_instructions
                )

                # ۲. تولید تصاویر
                image_prompts = []
                base_prompt = job.topic
                if job.image_instructions:
                    base_prompt = f"{job.topic} - {job.image_instructions}"
                image_prompts.append(base_prompt)

                blog_images = []
                instagram_images = []

                if job.blog_image_count > 0:
                    blog_images = await generate_images_with_ai(
                        prompts=image_prompts,
                        count=job.blog_image_count,
                        size="1024x1024"
                    )

                if job.instagram_image_count > 0:
                    instagram_images = await generate_images_with_ai(
                        prompts=image_prompts,
                        count=job.instagram_image_count,
                        size="1080x1080"
                    )

                # ۳. ایجاد پست
                post = Post(
                    topic=job.topic,
                    title=text_result.get("title", job.topic),
                    slug=text_result.get("slug", job.topic.lower().replace(" ", "-")[:200]),
                    body_html=text_result.get("body_html", ""),
                    summary=text_result.get("summary", ""),
                    instagram_caption=text_result.get("instagram_caption", ""),
                    hashtags=text_result.get("hashtags", ""),
                    instagram_status="draft",
                    website_status="published" if job.auto_publish else "draft",
                    ai_prompt=job.text_instructions,
                    ai_payload=json.dumps(text_result, ensure_ascii=False),
                    blog_enabled=True,
                    instagram_enabled=bool(job.instagram_image_count),
                )
                db.add(post)
                await db.commit()
                await db.refresh(post)

                # ۴. ذخیره تصاویر بلاگ
                for i, img_url in enumerate(blog_images):
                    if img_url:
                        asset = MediaAsset(
                            post_id=post.id,
                            role="blog_image",
                            prompt=image_prompts[0],
                            public_url=img_url,
                            sort_order=i,
                        )
                        db.add(asset)

                # ۵. ذخیره تصاویر اینستاگرام
                for i, img_url in enumerate(instagram_images):
                    if img_url:
                        asset = MediaAsset(
                            post_id=post.id,
                            role="instagram_image",
                            prompt=image_prompts[0],
                            public_url=img_url,
                            sort_order=i,
                        )
                        db.add(asset)

                await db.commit()

                # ۶. به‌روزرسانی Job
                job.status = "completed"
                job.post_id = post.id
                job.error_message = None
                await db.commit()

                return {
                    "success": True,
                    "job_id": job.id,
                    "post_id": post.id,
                    "blog_images": len(blog_images),
                    "instagram_images": len(instagram_images),
                }

            except Exception as exc:
                # ثبت خطا در Job
                result = await db.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = str(exc)[:1000]
                    await db.commit()

                # تلاش مجدد
                raise self.retry(exc=exc)

    # اجرای async در sync
    return _run_async(_process_async())
