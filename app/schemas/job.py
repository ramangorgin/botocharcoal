from datetime import date
from pydantic import BaseModel, Field, ConfigDict


class JobBaseSchema(BaseModel):
    subject: str = Field(..., min_length=3, max_length=512)
    instructions: str | None = Field(default=None, max_length=4096)

    duration_days: int = Field(default=1, ge=1, le=30)
    start_date: date = Field(default_factory=date.today)
    items_per_day: int = Field(default=1, ge=1, le=10)

    auto_publish_blog: bool = Field(default=False)
    blog_image_count: int = Field(default=1, ge=0, le=5)
    instagram_image_count: int = Field(default=4, ge=1, le=10)

    job_type: str = Field(default="general", max_length=64)


class JobCreateSchema(JobBaseSchema):
    pass


class JobUpdateSchema(BaseModel):
    subject: str | None = Field(default=None, min_length=3, max_length=512)
    instructions: str | None = Field(default=None, max_length=4096)

    duration_days: int | None = Field(default=None, ge=1, le=30)
    start_date: date | None = None
    items_per_day: int | None = Field(default=None, ge=1, le=10)

    auto_publish_blog: bool | None = None
    blog_image_count: int | None = Field(default=None, ge=0, le=5)
    instagram_image_count: int | None = Field(default=None, ge=1, le=10)
    job_type: str | None = Field(default=None, max_length=64)


class JobResponseSchema(JobBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    retry_count: int
    error_message: str | None = None
