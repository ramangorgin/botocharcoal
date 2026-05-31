from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.user import User
from app.core.security import verify_session_token
from sqlalchemy import select


async def get_current_admin(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get("admin_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_session_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.get(User, payload["uid"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return user
