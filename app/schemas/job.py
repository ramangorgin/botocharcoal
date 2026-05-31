from pydantic import BaseModel, Field
from typing import Literal


class JobCreateSchema(BaseModel):
    topic: str = Field(..., min_length=3, max_length=512)
    tone: str | None = Field(None, max_length=128)
    cta_text: str | None = Field(None, max_length=256)
    image_count: int = Field(default=4, ge=1, le=10)
