"""Create the initial admin user.

Usage:
    python -m scripts.create_admin

Environment variables (or .env file):
    ADMIN_USERNAME  — admin username (default: admin)
    ADMIN_PASSWORD  — admin password (default: Admin@123456)
    DATABASE_URL    — PostgreSQL connection string
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so imports work
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from app.db.session import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.security import hash_password
from app.db.models.user import User

DEFAULT_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
DEFAULT_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@123456")


async def create_admin_user() -> None:
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)

    async with AsyncSessionLocal() as db:
        # Check if admin already exists
        result = await db.execute(text(f"SELECT id FROM users WHERE username = :u"), {"u": DEFAULT_USERNAME})
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Admin user '{DEFAULT_USERNAME}' already exists (id={existing}). Skipping.")
            await engine.dispose()
            return

        password_hash = hash_password(DEFAULT_PASSWORD)
        admin = User(
            username=DEFAULT_USERNAME,
            password_hash=password_hash,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)

        print(f"Created admin user '{DEFAULT_USERNAME}' with id={admin.id}")
        print(f"Password: {DEFAULT_PASSWORD}")
        print("Please change this password after first login.")

        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin_user())
