# app/db/models/post.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)

    # Core content
    topic = Column(String(255))
    title = Column(String(255))
    slug = Column(String(255), unique=True, index=True)
    body_html = Column(Text)
    summary = Column(Text)

    # Instagram content
    instagram_caption = Column(Text)
    hashtags = Column(String(500))

    # Status
    website_status = Column(String(50), default="draft")  # draft, published
    instagram_status = Column(String(50), default="draft")  # draft, published
    published_to_website_at = Column(DateTime(timezone=True))

    # Source tracking
    source_type = Column(String(50), default="ai")  # ai, manual

    # AI metadata (for debugging/reference)
    ai_prompt = Column(Text)
    ai_payload = Column(JSON)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tags = relationship("Tag", secondary="post_tags", back_populates="posts")
    categories = relationship("Category", secondary="post_categories", back_populates="posts")
    media_assets = relationship("MediaAsset", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}')>"
