# app/schemas/job.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class JobBase(BaseModel):
    topic: str
    blog_text_instructions: Optional[str] = None
    blog_image_instructions: Optional[str] = None
    instagram_text_instructions: Optional[str] = None
    instagram_image_instructions: Optional[str] = None
    blog_image_count: int = 1
    instagram_image_count: int = 1
    auto_publish: bool = False


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    status: Optional[str] = None
    post_id: Optional[int] = None
    error_message: Optional[str] = None


class JobOut(JobBase):
    id: int
    status: str
    post_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
