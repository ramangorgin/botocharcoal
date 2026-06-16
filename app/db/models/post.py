from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)

    topic = Column(String(512), nullable=False)
    title = Column(String(512), nullable=False)
    slug = Column(String(512), unique=True, index=True)

    body_html = Column(Text)
    summary = Column(Text)
    category = Column(String(255))

    poster = Column(String(255))

    cover_image_url = Column(Text)

    instagram_caption = Column(Text)
    hashtags = Column(Text)

    instagram_status = Column(String(32), default="not_published")

    website_status = Column(String(32), default="draft")

    published_to_website_at = Column(DateTime(timezone=True))

    meta_title = Column(String(256))
    meta_description = Column(String(512))

    og_title = Column(String(512))
    og_description = Column(Text)
    og_image = Column(String(512))

    source_type = Column(String(20), default="ai")

    blog_enabled = Column(Boolean, default=True)
    instagram_enabled = Column(Boolean, default=True)

    ai_prompt = Column(Text)
    ai_payload = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    media_assets = relationship(
        "MediaAsset",
        back_populates="post",
        cascade="all, delete-orphan",
    )
