from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.catalog import Catalog


async def list_active_catalogs(db: AsyncSession) -> list[Catalog]:
    result = await db.execute(
        select(Catalog).where(Catalog.is_active == True).order_by(Catalog.created_at.desc())
    )
    return result.scalars().all()


async def create_catalog(title: str, file_path: str, public_url: str, db: AsyncSession) -> Catalog:
    cat = Catalog(title=title, file_path=file_path, public_url=public_url)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat
