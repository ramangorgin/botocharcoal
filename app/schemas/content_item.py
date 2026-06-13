from pydantic import BaseModel, Field
from datetime import datetime


class ContentItemResponseSchema(BaseModel):
    id: int
    job_id: int
    day_number: int
    status: str
    instagram_caption: str | None
    instagram_hashtags: str | None
    instagram_image_urls: str | None
    blog_title: str | None
    blog_slug: str | None
    blog_body: str | None
    blog_image_urls: str | None
    ai_response: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
