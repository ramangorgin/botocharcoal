from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)

    # -----------------------
    # Core content
    # -----------------------
    topic = Column(String(512), nullable=False)
    title = Column(String(512), nullable=False)
    slug = Column(String(512), nullable=False, unique=True, index=True)

    body_html = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    category = Column(String(255), nullable=True)
    poster = Column(String(255), nullable=True)  # author name

    cover_image_url = Column(Text, nullable=True)

    # -----------------------
    # Instagram
    # -----------------------
    instagram_caption = Column(Text, nullable=True)
    hashtags = Column(Text, nullable=True)

    instagram_status = Column(
        String(32),
        nullable=False,
        default="not_published",
    )

    instagram_media_id = Column(String(128), nullable=True)
    published_to_instagram_at = Column(DateTime(timezone=True), nullable=True)

    # -----------------------
    # Website
    # -----------------------
    website_status = Column(
        String(32),
        nullable=False,
        default="draft",
    )

    published_to_website_at = Column(DateTime(timezone=True), nullable=True)

    # SEO
    meta_title = Column(String(256), nullable=True)
    meta_description = Column(String(512), nullable=True)
    og_title = Column(String(512), nullable=True)
    og_description = Column(Text, nullable=True)
    og_image = Column(String(512), nullable=True)

    # -----------------------
    # Flow Control
    # -----------------------
    source_type = Column(String(20), nullable=False, default="manual")  # manual | ai

    blog_enabled = Column(Boolean, nullable=False, default=True)
    instagram_enabled = Column(Boolean, nullable=False, default=True)

    scheduled_for = Column(DateTime(timezone=True), nullable=True)

    ai_payload = Column(JSON, nullable=True)

    # -----------------------
    # Foreign Keys
    # -----------------------
    job_id = Column(
        Integer,
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    content_item_id = Column(
        Integer,
        ForeignKey("content_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # -----------------------
    # Relationships
    # -----------------------
    job = relationship("Job", back_populates="posts")
    content_item = relationship("ContentItem", back_populates="post")

    media_assets = relationship(
        "MediaAsset",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="MediaAsset.sort_order",
        passive_deletes=True,
    )

    # -----------------------
    # Timestamps
    # -----------------------
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
