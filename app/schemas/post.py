# app/schemas/post.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PostBase(BaseModel):
    topic: str
    title: str
    slug: str
    body_html: Optional[str] = None
    summary: Optional[str] = None
    instagram_caption: Optional[str] = None
    hashtags: Optional[str] = None


class PostCreate(BaseModel):
    topic: str
    text_instruction: Optional[str] = None
    image_instruction: Optional[str] = None
    blog_image_count: int = 1
    instagram_image_count: int = 3
    auto_publish_blog: bool = False


class PostUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    body_html: Optional[str] = None
    summary: Optional[str] = None
    instagram_caption: Optional[str] = None
    hashtags: Optional[str] = None
    website_status: Optional[str] = None
    instagram_status: Optional[str] = None


class PostOut(PostBase):
    id: int
    website_status: str
    instagram_status: str
    source_type: str
    published_to_website_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
