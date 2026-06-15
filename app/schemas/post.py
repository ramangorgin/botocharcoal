from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class PostBaseSchema(BaseModel):
    topic: str | None = Field(default=None, max_length=512)
    title: str | None = Field(default=None, max_length=512)
    slug: str | None = Field(default=None, max_length=512)

    body_html: str | None = None
    summary: str | None = None
    category: str | None = None
    cover_image_url: str | None = None
    instagram_caption: str | None = None
    hashtags: str | None = None

    website_status: str = Field(default="draft")
    instagram_status: str = Field(default="not_published")

    published_to_website_at: datetime | None = None
    published_to_instagram_at: datetime | None = None

    meta_title: str | None = None
    meta_description: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None

    blog_enabled: bool = True
    instagram_enabled: bool = True

    source_type: str = "ai"

    ai_payload: dict[str, Any] | None = None

    job_id: int | None = None


class PostCreateSchema(PostBaseSchema):
    pass


class PostUpdateSchema(BaseModel):
    topic: str | None = None
    title: str | None = None
    slug: str | None = None

    body_html: str | None = None
    summary: str | None = None
    category: str | None = None

    instagram_caption: str | None = None
    hashtags: str | None = None

    website_status: str | None = None
    instagram_status: str | None = None

    meta_title: str | None = None
    meta_description: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None

    blog_enabled: bool | None = None
    instagram_enabled: bool | None = None

    ai_payload: dict | None = None


class PostResponseSchema(PostBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
