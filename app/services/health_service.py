import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis
from app.core.config import settings
from app.schemas.settings import HealthStatus


async def check_health(db: AsyncSession) -> HealthStatus:
    # DB
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    # Redis
    redis_ok = False
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        pass

    # Media writable
    media_ok = False
    try:
        p = Path(settings.MEDIA_ROOT)
        p.mkdir(parents=True, exist_ok=True)
        test_file = p / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        media_ok = True
    except Exception:
        pass

    return HealthStatus(
        database=db_ok,
        redis=redis_ok,
        media_writable=media_ok,
        openai_key_set=bool(settings.OPENAI_API_KEY),
        text_model_set=bool(settings.TEXT_MODEL),
        image_model_set=bool(settings.IMAGE_MODEL),
        instagram_token_set=bool(settings.IG_LONG_LIVED_ACCESS_TOKEN),
        instagram_account_set=bool(settings.IG_BUSINESS_ACCOUNT_ID),
    )
