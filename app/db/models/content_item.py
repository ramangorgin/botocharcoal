from sqlalchemy import String, Integer, Text, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.db.base import Base
from app.core.constants import JobStatus


class ContentItem(Base):
    __tablename__ = "content_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))

    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(
            JobStatus,
            name="contentitemstatus",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=JobStatus.PENDING,
    )

    instagram_caption: Mapped[str | None] = mapped_column(Text)
    instagram_hashtags: Mapped[str | None] = mapped_column(Text)
    instagram_image_urls: Mapped[str | None] = mapped_column(Text)  # JSON array string

    blog_title: Mapped[str | None] = mapped_column(String(512))
    blog_slug: Mapped[str | None] = mapped_column(String(512))
    blog_body: Mapped[str | None] = mapped_column(Text)
    blog_image_urls: Mapped[str | None] = mapped_column(Text)  # JSON array string

    ai_response: Mapped[str | None] = mapped_column(Text)  # Raw JSON response from AI

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
