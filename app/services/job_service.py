from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.job import Job
from app.schemas.job import JobCreateSchema
from app.core.constants import JobStatus


async def create_job(data: JobCreateSchema, db: AsyncSession) -> Job:
    job = Job(**data.model_dump())
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(job_id: int, db: AsyncSession) -> Job | None:
    return await db.get(Job, job_id)


async def list_jobs(db: AsyncSession, limit: int = 50) -> list[Job]:
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


async def update_job_status(job: Job, status: JobStatus, db: AsyncSession, error: str | None = None) -> None:
    job.status = status.value if isinstance(status, JobStatus) else status
    if error:
        job.error_message = error
    await db.commit()
