from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_current_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/jobs", response_class=HTMLResponse)
async def jobs_index(
    request: Request,
    admin=Depends(get_current_admin)
):
    return templates.TemplateResponse(
        "admin/jobs/index.html",
        {"request": request}
    )


@router.get("/jobs/create", response_class=HTMLResponse)
async def jobs_create(
    request: Request,
    admin=Depends(get_current_admin)
):
    return templates.TemplateResponse(
        "admin/jobs/create.html",
        {"request": request}
    )


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def jobs_show(
    request: Request,
    job_id: int,
    admin=Depends(get_current_admin)
):
    return templates.TemplateResponse(
        "admin/jobs/show.html",
        {
            "request": request,
            "job_id": job_id
        }
    )
