from pydantic import BaseModel, Field
from typing import Literal
from datetime import date


class JobCreateSchema(BaseModel):
    subject: str = Field(..., min_length=3, max_length=512)
    instructions: str | None = Field(None, max_length=4096)

    duration_days: int = Field(default=1, ge=1, le=30)
    start_date: date = Field(default_factory=lambda: date.today())
    items_per_day: int = Field(default=1, ge=1, le=10)

    auto_publish_blog: bool = Field(default=False)
    blog_image_count: int = Field(default=1, ge=0, le=5)
    instagram_image_count: int = Field(default=4, ge=1, le=10)
    job_type: str = Field(default="general", max_length=64)


class JobResponseSchema(BaseModel):
    id: int
    subject: str
    instructions: str | None
    duration_days: int
    start_date: date
    items_per_day: int
    auto_publish_blog: bool
    blog_image_count: int
    instagram_image_count: int
    job_type: str
    status: str
    retry_count: int
    error_message: str | None
    blog_title: str | None
    blog_slug: str | None
    blog_body: str | None
    started_at: str | None
    finished_at: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
