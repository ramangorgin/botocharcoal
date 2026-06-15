from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True)

    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    job_id = Column(
        Integer,
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    role = Column(String(50), nullable=False)  # instagram | blog_cover | og_image

    prompt = Column(Text, nullable=True)

    local_path = Column(Text, nullable=True)
    public_url = Column(Text, nullable=True)

    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    sort_order = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    post = relationship("Post", back_populates="media_assets")
    job = relationship("Job", back_populates="media_assets")
