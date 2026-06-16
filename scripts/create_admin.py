import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# load .env explicitly
load_dotenv(PROJECT_ROOT / ".env")

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.user import User


ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123456")


def validate_database_url(url: str) -> None:
    if not url:
        raise RuntimeError("DATABASE_URL is empty or not loaded.")
    if "://" not in url:
        raise RuntimeError(f"DATABASE_URL looks invalid: {url!r}")


async def create_admin_user() -> None:
    db_url = settings.DATABASE_URL
    validate_database_url(db_url)

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with SessionLocal() as db:
            # check if user already exists
            stmt = text("SELECT id FROM users WHERE username = :u LIMIT 1")
            result = await db.execute(stmt, {"u": ADMIN_USERNAME})
            existing = result.scalar_one_or_none()

            if existing is not None:
                print(f"Admin user already exists: {ADMIN_USERNAME}")
                return

            # create admin user
            user = User(
                username=ADMIN_USERNAME,
                password_hash=hash_password(ADMIN_PASSWORD),
                is_admin=True,
            )

            db.add(user)
            await db.commit()

            print("Admin user created successfully.")
            print(f"Username: {ADMIN_USERNAME}")
            print(f"Password: {ADMIN_PASSWORD}")

    except SQLAlchemyError as exc:
        raise RuntimeError(f"Database error while creating admin user: {exc}") from exc
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin_user())
