from sqlalchemy import String, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.db.base import Base
from app.core.constants import PostWebsiteStatus, PostInstagramStatus


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(512))
    slug: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text)
    instagram_caption: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[str | None] = mapped_column(Text)

    # SEO fields
    meta_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    og_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    og_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    og_image: Mapped[str | None] = mapped_column(String(512), nullable=True)

    website_status: Mapped[str] = mapped_column(
        SAEnum(PostWebsiteStatus, name="postwebsitestatus"),
        default=PostWebsiteStatus.DRAFT,
    )
    instagram_status: Mapped[str] = mapped_column(
        SAEnum(PostInstagramStatus, name="postinstagramstatus"),
        default=PostInstagramStatus.NOT_PUBLISHED,
    )
    instagram_media_id: Mapped[str | None] = mapped_column(String(128))
    published_to_website_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_to_instagram_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
