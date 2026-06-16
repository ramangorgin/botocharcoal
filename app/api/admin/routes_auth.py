from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.templating import Jinja2Templates

from app.db.session import get_db
from app.db.models import User
from app.core.security import verify_password, create_session_token

router = APIRouter()

templates = Jinja2Templates(directory="app/templates/admin")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": error,
        },
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.username == username)
    )

    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "نام کاربری یا رمز اشتباه است",
            },
        )

    token = create_session_token(user.id)

    response = RedirectResponse("/admin/dashboard", status_code=302)

    response.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,
    )

    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie("admin_session")
    return response
