# app/tasks/generate_post.py
import asyncio
import json
import logging
import re
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session
from app.db.models.job import Job
from app.db.models.post import Post
from app.db.models.media_asset import MediaAsset
from app.services.ai_service import generate_content_with_ai, generate_images_with_ai, download_and_save_image

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


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


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    name='app.tasks.generate_post.process_job_task',
)
def process_job_task(self, job_id: int):
    """
    تسک Celery برای پردازش Job
    تولید محتوای جداگانه برای بلاگ و اینستاگرام
    """

    async def _process_async():
        async with async_session() as db:
            try:
                logger.info(f"🚀 Starting job processing for job_id={job_id}")

                # دریافت Job
                result = await db.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job:
                    logger.error(f"❌ Job with id {job_id} not found")
                    return {"error": f"Job with id {job_id} not found"}

                # به‌روزرسانی وضعیت به processing
                job.status = "processing"
                await db.commit()
                logger.info(f"📊 Job status updated to 'processing'")

                # ==========================================
                # ۱. تولید محتوای بلاگ
                # ==========================================
                logger.info("=" * 60)
                logger.info("📝 GENERATING BLOG CONTENT")

                blog_instructions = job.blog_text_instructions or ""
                if not blog_instructions:
                    blog_instructions = "یک مقاله کامل و جامع با فرمت HTML تولید کن. شامل تگ‌های h2, h3, p, ul, li, strong, blockquote باشد. مقاله باید حداقل ۱۰۰۰ کلمه و دارای بخش‌های مقدمه، بدنه اصلی و نتیجه‌گیری باشد."

                blog_content = await generate_content_with_ai(
                    topic=job.topic,
                    instructions=blog_instructions
                )
                logger.info(f"✅ Blog content generated")

                # Wait to avoid rate limits
                await asyncio.sleep(3)

                # ==========================================
                # ۲. تولید کپشن اینستاگرام
                # ==========================================
                logger.info("=" * 60)
                logger.info("📝 GENERATING INSTAGRAM CONTENT")

                instagram_instructions = job.instagram_text_instructions or ""
                if not instagram_instructions:
                    instagram_instructions = "یک کپشن جذاب و کوتاه برای اینستاگرام بنویس. شامل: یک سوال تعاملی در ابتدا، متن اصلی (حداکثر ۱۵۰ کلمه)، و ۱۰-۱۵ هشتگ مرتبط در پایان. لحن متن باید صمیمی و خودمانی باشد."

                instagram_content = await generate_content_with_ai(
                    topic=job.topic,
                    instructions=instagram_instructions
                )
                logger.info(f"✅ Instagram content generated")

                # Wait to avoid rate limits
                await asyncio.sleep(3)

                # ==========================================
                # ۳. تولید تصاویر بلاگ (کاور)
                # ==========================================
                logger.info("=" * 60)
                logger.info("🖼️  GENERATING BLOG COVER IMAGE")

                blog_image_prompts = []
                if job.blog_image_instructions:
                    blog_image_prompts.append(
                        f"Professional blog cover image: {job.topic} - {job.blog_image_instructions}"
                    )
                else:
                    blog_image_prompts.append(
                        f"Professional blog cover image for article about: {job.topic}. Clean, modern design."
                    )

                blog_images = []
                if job.blog_image_count > 0:
                    blog_images = await generate_images_with_ai(
                        prompts=blog_image_prompts,
                        count=job.blog_image_count,
                    )
                    logger.info(f"✅ Generated {len(blog_images)} blog images")

                    # Wait before next image generation
                    if job.instagram_image_count > 0:
                        await asyncio.sleep(5)
                else:
                    logger.info("   Skipping blog images (count=0)")

                # ==========================================
                # ۴. تولید تصاویر اینستاگرام
                # ==========================================
                logger.info("=" * 60)
                logger.info("🖼️  GENERATING INSTAGRAM IMAGES")

                instagram_image_prompts = []
                if job.instagram_image_instructions:
                    instagram_image_prompts.append(
                        f"Instagram post image (square): {job.topic} - {job.instagram_image_instructions}"
                    )
                else:
                    instagram_image_prompts.append(
                        f"Instagram post image (square format) about: {job.topic}. Modern style."
                    )

                instagram_images = []
                if job.instagram_image_count > 0:
                    instagram_images = await generate_images_with_ai(
                        prompts=instagram_image_prompts,
                        count=job.instagram_image_count,
                    )
                    logger.info(f"✅ Generated {len(instagram_images)} instagram images")
                else:
                    logger.info("   Skipping instagram images (count=0)")

                # ==========================================
                # ۵. ایجاد پست در دیتابیس
                # ==========================================
                logger.info("=" * 60)
                logger.info("💾 CREATING POST IN DATABASE")

                title = blog_content.get("title", job.topic)
                slug = blog_content.get("slug", "")
                if not slug:
                    slug = re.sub(r'[^\w\-]', '', title.lower().replace(" ", "-")[:200])

                body_html = blog_content.get("body_html", blog_content.get("content", ""))

                summary = blog_content.get("summary", "")
                if not summary and body_html:
                    clean_text = re.sub(r'<[^>]+>', '', body_html)
                    summary = clean_text[:200] + "..." if len(clean_text) > 200 else clean_text

                instagram_caption = instagram_content.get(
                    "instagram_caption",
                    instagram_content.get("caption", instagram_content.get("content", ""))
                )
                hashtags = instagram_content.get("hashtags", instagram_content.get("tags", ""))
                if isinstance(hashtags, list):
                    hashtags = " ".join(hashtags)

                logger.info(f"   Title: {title}")
                logger.info(f"   Slug: {slug}")
                logger.info(f"   Body HTML length: {len(body_html)}")
                logger.info(f"   Hashtags: {hashtags[:100]}")

                post = Post(
                    topic=job.topic,
                    title=title,
                    slug=slug,
                    body_html=body_html,
                    summary=summary,
                    instagram_caption=instagram_caption,
                    hashtags=hashtags,
                    instagram_status="draft",
                    website_status="published" if job.auto_publish else "draft",
                    source_type="ai",
                    ai_prompt=json.dumps({
                        "blog_text_instructions": job.blog_text_instructions,
                        "blog_image_instructions": job.blog_image_instructions,
                        "instagram_text_instructions": job.instagram_text_instructions,
                        "instagram_image_instructions": job.instagram_image_instructions,
                    }, ensure_ascii=False),
                    ai_payload=json.dumps({
                        "blog_content": blog_content,
                        "instagram_content": instagram_content,
                    }, ensure_ascii=False),
                )
                db.add(post)
                await db.commit()
                await db.refresh(post)
                logger.info(f"✅ Post created with id={post.id}")

                # ==========================================
                # ۶. ذخیره تصاویر بلاگ (کاور)
                # ==========================================
                logger.info("=" * 60)
                logger.info("💾 SAVING BLOG COVER IMAGE")

                for i, img_url in enumerate(blog_images[:1]):
                    if img_url:
                        logger.info(f"   Downloading blog cover image...")
                        local_path = await download_and_save_image(img_url, f"blog_cover_{post.id}")

                        asset = MediaAsset(
                            post_id=post.id,
                            role="blog_cover",
                            prompt=blog_image_prompts[0] if blog_image_prompts else "",
                            public_url=local_path if local_path else img_url,
                            sort_order=0,
                        )
                        db.add(asset)
                        logger.info(f"   ✅ Blog cover image saved")

                await db.commit()

                # ==========================================
                # ۷. ذخیره تصاویر اینستاگرام
                # ==========================================
                logger.info("=" * 60)
                logger.info("💾 SAVING INSTAGRAM IMAGES")

                for i, img_url in enumerate(instagram_images):
                    if img_url:
                        logger.info(f"   Downloading instagram image {i+1}/{len(instagram_images)}...")
                        local_path = await download_and_save_image(img_url, f"instagram_{post.id}_{i}")

                        asset = MediaAsset(
                            post_id=post.id,
                            role="instagram_image",
                            prompt=instagram_image_prompts[0] if instagram_image_prompts else "",
                            public_url=local_path if local_path else img_url,
                            sort_order=i,
                        )
                        db.add(asset)

                await db.commit()

                # ==========================================
                # ۸. به‌روزرسانی Job
                # ==========================================
                job.status = "completed"
                job.post_id = post.id
                job.error_message = None
                await db.commit()

                logger.info("=" * 60)
                logger.info(f"🎉 JOB {job_id} COMPLETED SUCCESSFULLY!")
                logger.info(f"   Post ID: {post.id}")
                logger.info(f"   Blog images: {len(blog_images)}")
                logger.info(f"   Instagram images: {len(instagram_images)}")
                logger.info("=" * 60)

                return {
                    "success": True,
                    "job_id": job.id,
                    "post_id": post.id,
                    "blog_images": len(blog_images),
                    "instagram_images": len(instagram_images),
                }

            except Exception as exc:
                logger.error(f"❌ JOB {job_id} FAILED: {str(exc)}")
                logger.error(f"   Error type: {type(exc).__name__}")

                try:
                    result = await db.execute(select(Job).where(Job.id == job_id))
                    job = result.scalar_one_or_none()
                    if job:
                        job.status = "failed"
                        job.error_message = str(exc)[:1000]
                        await db.commit()
                except Exception as db_error:
                    logger.error(f"❌ Failed to update job error status: {str(db_error)}")

                raise self.retry(exc=exc)

    return _run_async(_process_async())
