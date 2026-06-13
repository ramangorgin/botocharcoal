from sqlalchemy import String, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.db.base import Base


class AISettings(Base):
    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), default="openai")
    api_key: Mapped[str | None] = mapped_column(String(512))
    api_base_url: Mapped[str | None] = mapped_column(String(512))

    text_model: Mapped[str | None] = mapped_column(String(128))
    image_model: Mapped[str | None] = mapped_column(String(128))

    prompt_template: Mapped[str | None] = mapped_column(Text)  # JSON for custom prompts

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
