from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(255))
    title = Column(String(255))
    slug = Column(String(255), unique=True, index=True)
    body_html = Column(Text)
    summary = Column(Text)
    category = Column(String(100))  # این ستون قدیمی رو نگه می‌داریم
    poster = Column(String(255))
    cover_image_url = Column(String(500))
    instagram_caption = Column(Text)
    hashtags = Column(String(500))
    instagram_status = Column(String(50))
    website_status = Column(String(50))
    published_to_website_at = Column(DateTime)
    meta_title = Column(String(255))
    meta_description = Column(String(500))
    og_title = Column(String(255))
    og_description = Column(String(500))
    og_image = Column(String(500))
    source_type = Column(String(50))
    blog_enabled = Column(Boolean, default=True)
    instagram_enabled = Column(Boolean, default=True)
    ai_prompt = Column(Text)
    ai_payload = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # رابطه‌های many-to-many جدید
    tags = relationship("Tag", secondary="post_tags", back_populates="posts")
    categories = relationship("Category", secondary="post_categories", back_populates="posts")

    # رابطه‌ای که از قبل وجود داره
    media_assets = relationship("MediaAsset", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}')>"
