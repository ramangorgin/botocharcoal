from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.user import User
from app.api.deps import get_current_admin
from app.services.catalog_service import list_active_catalogs, create_catalog
from app.services.media_storage import save_upload

router = APIRouter()
templates = Jinja2Templates(directory="app/templates/admin")


@router.get("/catalog", response_class=HTMLResponse)
async def catalog_list(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    catalogs = await list_active_catalogs(db)
    return templates.TemplateResponse("catalog_list.html", {"request": request, "catalogs": catalogs})


@router.post("/catalog/upload")
async def upload_catalog(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    content = await file.read()
    local_path, public_url = await save_upload(content, file.filename, subfolder="catalogs")
    await create_catalog(title, local_path, public_url, db)
    return RedirectResponse("/admin/catalog", status_code=302)
