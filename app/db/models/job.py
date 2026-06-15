from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)

    subject = Column(String(512), nullable=False)
    instructions = Column(Text, nullable=True)

    duration_days = Column(Integer, nullable=False, default=1)
    start_date = Column(Date, nullable=True)
    items_per_day = Column(Integer, nullable=False, default=1)

    auto_publish_blog = Column(Boolean, nullable=False, default=False)
    blog_image_count = Column(Integer, nullable=False, default=1)
    instagram_image_count = Column(Integer, nullable=False, default=4)
    job_type = Column(String(64), nullable=False, default="general")

    status = Column(String(32), nullable=False, default="pending")

    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    posts = relationship(
        "Post",
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    media_assets = relationship(
        "MediaAsset",
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
