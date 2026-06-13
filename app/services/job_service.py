"""
Botocharcoal Job Service
-------------------------
Manages job lifecycle, content item creation, and status tracking.
"""

import json
from datetime import date, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.job import Job
from app.db.models.content_item import ContentItem
from app.schemas.job import JobCreateSchema
from app.core.constants import JobStatus
from app.core.logging import logger


async def create_job(data: JobCreateSchema, db: AsyncSession) -> Job:
    """Create a new job and its content items."""
    job = Job(
        subject=data.subject,
        instructions=data.instructions,
        duration_days=data.duration_days,
        start_date=data.start_date,
        items_per_day=data.items_per_day,
        auto_publish_blog=data.auto_publish_blog,
        blog_image_count=data.blog_image_count,
        instagram_image_count=data.instagram_image_count,
        job_type=data.job_type,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Pre-create content items for each day
    await _create_content_items_for_job(job, db)
    
    logger.info("job_created", job_id=job.id, subject=data.subject, items=data.duration_days * data.items_per_day)
    return job


async def _create_content_items_for_job(job: Job, db: AsyncSession) -> list[ContentItem]:
    """Create ContentItem rows for each day of the job."""
    content_items = []
    
    for day_num in range(1, job.duration_days + 1):
        for item_idx in range(1, job.items_per_day + 1):
            ci = ContentItem(
                job_id=job.id,
                day_number=day_num,
                status=JobStatus.PENDING,
            )
            db.add(ci)
            content_items.append(ci)
    
    await db.commit()
    for ci in content_items:
        await db.refresh(ci)
    
    logger.info("content_items_created", job_id=job.id, count=len(content_items))
    return content_items


async def get_job(job_id: int, db: AsyncSession) -> Job | None:
    """Get a job by ID."""
    return await db.get(Job, job_id)


async def get_job_with_items(job_id: int, db: AsyncSession) -> dict | None:
    """Get a job with its content items."""
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalars().first()
    if not job:
        return None
    
    items_result = await db.execute(
        select(ContentItem)
        .where(ContentItem.job_id == job_id)
        .order_by(ContentItem.day_number, ContentItem.id)
    )
    items = items_result.scalars().all()
    
    return {"job": job, "items": items}


async def list_jobs(db: AsyncSession, limit: int = 50) -> list[Job]:
    """List jobs ordered by creation date (newest first)."""
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


async def update_job_status(job: Job, status: JobStatus, db: AsyncSession, error: str | None = None) -> None:
    """Update job status with optional error message."""
    job.status = status.value if isinstance(status, JobStatus) else status
    if error:
        job.error_message = error
    await db.commit()


async def get_job_content_items(job_id: int, db: AsyncSession) -> list[ContentItem]:
    """Get all content items for a job."""
    result = await db.execute(
        select(ContentItem)
        .where(ContentItem.job_id == job_id)
        .order_by(ContentItem.day_number, ContentItem.id)
    )
    return result.scalars().all()
