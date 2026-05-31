from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models.lead import Lead
from app.schemas.lead import LeadCreateSchema
from datetime import datetime, timezone


async def create_lead(data: LeadCreateSchema, db: AsyncSession) -> Lead:
    lead = Lead(**data.model_dump())
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


async def list_leads(db: AsyncSession, contacted: bool | None = None) -> list[Lead]:
    q = select(Lead).order_by(Lead.created_at.desc())
    if contacted is not None:
        q = q.where(Lead.contacted == contacted)
    result = await db.execute(q)
    return result.scalars().all()


async def mark_contacted(lead_id: int, db: AsyncSession) -> Lead | None:
    lead = await db.get(Lead, lead_id)
    if not lead:
        return None
    lead.contacted = True
    lead.contacted_at = datetime.now(timezone.utc)
    await db.commit()
    return lead
