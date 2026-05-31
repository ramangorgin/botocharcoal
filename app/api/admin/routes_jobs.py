from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.user import User
from app.api.deps import get_current_admin
from app.services.job_service import create_job, list_jobs, get_job
from app.schemas.job import JobCreateSchema
from app.tasks.content_pipeline import run_content_pipeline
from app.core.constants import JobStatus

router = APIRouter()
templates = Jinja2Templates(directory="app/templates/admin")


@router.get("/jobs", response_class=HTMLResponse)
async def jobs_list(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    jobs = await list_jobs(db)
    return templates.TemplateResponse("jobs_list.html", {"request": request, "jobs": jobs})


@router.get("/jobs/create", response_class=HTMLResponse)
async def job_create_page(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    return templates.TemplateResponse("job_create.html", {"request": request})


@router.post("/jobs/create")
async def create_job_route(
    request: Request,
    topic: str = Form(...),
    tone: str = Form(None),
    cta_text: str = Form(None),
    image_count: int = Form(4),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    schema = JobCreateSchema(topic=topic, tone=tone, cta_text=cta_text, image_count=image_count)
    job = await create_job(schema, db)
    job.status = JobStatus.QUEUED
    await db.commit()
    await db.refresh(job)
    run_content_pipeline.delay(job.id)
    return RedirectResponse(f"/admin/jobs/{job.id}", status_code=302)


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail(job_id: int, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    job = await get_job(job_id, db)
    if not job:
        return HTMLResponse("Job not found", status_code=404)
    return templates.TemplateResponse("job_detail.html", {"request": request, "job": job})


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: int, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    job = await get_job(job_id, db)
    if not job:
        return HTMLResponse("Job not found", status_code=404)
    job.status = JobStatus.QUEUED
    job.retry_count += 1
    job.error_message = None
    await db.commit()
    run_content_pipeline.delay(job.id)
    return RedirectResponse(f"/admin/jobs/{job_id}", status_code=302)
