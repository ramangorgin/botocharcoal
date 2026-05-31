from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.user import User
from app.api.deps import get_current_admin
from app.services.lead_service import list_leads, mark_contacted

router = APIRouter()
templates = Jinja2Templates(directory="app/templates/admin")


@router.get("/leads", response_class=HTMLResponse)
async def leads_list(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    leads = await list_leads(db)
    return templates.TemplateResponse("leads_list.html", {"request": request, "leads": leads})


@router.post("/leads/{lead_id}/contacted")
async def mark_lead_contacted(lead_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    await mark_contacted(lead_id, db)
    return RedirectResponse("/admin/leads", status_code=302)
