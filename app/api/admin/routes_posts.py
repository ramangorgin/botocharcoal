from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_current_admin

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/posts", response_class=HTMLResponse)
async def posts_index(
    request: Request,
    admin=Depends(get_current_admin)
):
    return templates.TemplateResponse(
        "admin/posts/index.html",
        {"request": request}
    )


@router.get("/posts/create", response_class=HTMLResponse)
async def posts_create(
    request: Request,
    admin=Depends(get_current_admin)
):
    return templates.TemplateResponse(
        "admin/posts/create.html",
        {"request": request}
    )


@router.get("/posts/{post_id}", response_class=HTMLResponse)
async def posts_show(
    request: Request,
    post_id: int,
    admin=Depends(get_current_admin)
):
    return templates.TemplateResponse(
        "admin/posts/show.html",
        {
            "request": request,
            "post_id": post_id
        }
    )


@router.get("/posts/{post_id}/edit", response_class=HTMLResponse)
async def posts_edit(
    request: Request,
    post_id: int,
    admin=Depends(get_current_admin)
):
    return templates.TemplateResponse(
        "admin/posts/edit.html",
        {
            "request": request,
            "post_id": post_id
        }
    )
