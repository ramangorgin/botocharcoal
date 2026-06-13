from sqlalchemy import String, Integer, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date, timezone
from app.db.base import Base
from app.core.constants import JobStatus


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text)

    duration_days: Mapped[int] = mapped_column(Integer, default=1)
    start_date: Mapped[date] = mapped_column(default=lambda: date.today())
    items_per_day: Mapped[int] = mapped_column(Integer, default=1)

    auto_publish_blog: Mapped[bool] = mapped_column(default=False)
    blog_image_count: Mapped[int] = mapped_column(Integer, default=1)
    instagram_image_count: Mapped[int] = mapped_column(Integer, default=4)
    job_type: Mapped[str] = mapped_column(String(64), default="general")

    status: Mapped[JobStatus] = mapped_column(
        SAEnum(
            JobStatus,
            name="jobstatus",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=JobStatus.PENDING,
    )

    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)

    blog_title: Mapped[str | None] = mapped_column(String(512))
    blog_slug: Mapped[str | None] = mapped_column(String(512))
    blog_body: Mapped[str | None] = mapped_column(Text)

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
