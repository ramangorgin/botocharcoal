from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Async engine (برای FastAPI)
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Sync engine (برای Celery tasks)
# توجه: اگر DATABASE_URL با پیشوند async باشد (مثلاً postgresql+asyncpg)، باید آن را به sync تبدیل کنید.
# معمولاً با حذف +asyncpg از انتهای URL می‌توانید به postgresql:// برسید.
sync_database_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")
engine = create_engine(sync_database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
async_session = AsyncSessionLocal
