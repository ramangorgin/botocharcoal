from celery.schedules import crontab
from app.tasks.celery_app import celery_app


celery_app.conf.beat_schedule = {
    # Retry failed jobs every hour
    "retry-failed-jobs": {
        "task": "tasks.retry_failed_jobs",
        "schedule": crontab(minute=0),
    },
}


@celery_app.task(name="tasks.retry_failed_jobs")
def retry_failed_jobs() -> None:
    import asyncio
    from app.db.session import AsyncSessionLocal
    from app.db.models.job import Job
    from app.core.constants import JobStatus
    from sqlalchemy import select

    async def _retry():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Job)
                .where(Job.status == JobStatus.FAILED)
                .where(Job.retry_count < 3)
            )
            jobs = result.scalars().all()
            for job in jobs:
                job.status = JobStatus.QUEUED
                from app.tasks.content_pipeline import run_content_pipeline
                run_content_pipeline.delay(job.id)
            await db.commit()

    asyncio.get_event_loop().run_until_complete(_retry())
