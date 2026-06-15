from sqlalchemy import (
    String,
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True)

    job_id = Column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    day_number = Column(Integer, nullable=False)

    status = Column(String(32), nullable=False, default="pending")

    instagram_caption = Column(Text, nullable=True)
    instagram_hashtags = Column(Text, nullable=True)
    instagram_image_urls = Column(Text, nullable=True)

    blog_title = Column(Text, nullable=True)
    blog_slug = Column(Text, nullable=True)
    blog_body = Column(Text, nullable=True)
    blog_image_urls = Column(Text, nullable=True)

    ai_response = Column(Text, nullable=True)

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

    # relationships
    job = relationship("Job")
    post = relationship(
        "Post",
        back_populates="content_item",
        uselist=False,
    )
