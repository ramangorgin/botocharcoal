from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.templating import Jinja2Templates

from app.db.session import get_db
from app.db.models import AISettings
from app.api.admin.dependencies import get_current_admin

router = APIRouter()

templates = Jinja2Templates(directory="app/templates/admin")


@router.get("/ai-settings", response_class=HTMLResponse)
async def ai_settings_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):

    result = await db.execute(select(AISettings))
    settings = result.scalar_one_or_none()

    return templates.TemplateResponse(
        "ai_settings.html",
        {
            "request": request,
            "settings": settings,  # Make sure this matches the template variable name
        },
    )


@router.post("/ai-settings")
async def update_ai_settings(
    request: Request,
    provider: str = Form(...),
    api_key: str = Form(...),
    base_url: str = Form(""),
    text_model: str = Form(...),
    image_model: str = Form(...),
    system_prompt: str = Form(""),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_admin),
):

    result = await db.execute(select(AISettings))
    settings = result.scalar_one_or_none()

    if not settings:
        settings = AISettings(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            text_model=text_model,
            image_model=image_model,
            system_prompt=system_prompt,
        )
        db.add(settings)

    else:
        settings.provider = provider
        settings.api_key = api_key
        settings.base_url = base_url
        settings.text_model = text_model
        settings.image_model = image_model
        settings.system_prompt = system_prompt

    await db.commit()

    # Check if it's an AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Settings saved successfully"})

    # For non-AJAX requests, redirect with success message
    return RedirectResponse("/admin/jobs/?msg=saved", status_code=302)
