from fastapi import Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User
from app.core.security import decode_session_token


async def get_current_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
):

    token = request.cookies.get("admin_session")

    if not token:
        raise HTTPException(status_code=401)

    user_id = decode_session_token(token)

    if not user_id:
        raise HTTPException(status_code=401)

    user = await db.get(User, user_id)

    if not user or not user.is_admin:
        raise HTTPException(status_code=403)

    return user
