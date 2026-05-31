from sqlalchemy import String, Integer, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.db.base import Base
from app.core.constants import JobStatus


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(512), nullable=False)
    tone: Mapped[str | None] = mapped_column(String(128))
    cta_text: Mapped[str | None] = mapped_column(String(256))
    image_count: Mapped[int] = mapped_column(Integer, default=4)
    status: Mapped[str] = mapped_column(
        SAEnum(JobStatus, name="jobstatus"), default=JobStatus.PENDING
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    logs_text: Mapped[str | None] = mapped_column(Text)

    generated_caption: Mapped[str | None] = mapped_column(Text)
    generated_hashtags: Mapped[str | None] = mapped_column(Text)
    generated_blog_title: Mapped[str | None] = mapped_column(String(512))
    generated_blog_slug: Mapped[str | None] = mapped_column(String(512))
    generated_blog_body: Mapped[str | None] = mapped_column(Text)
    generated_image_prompts: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
