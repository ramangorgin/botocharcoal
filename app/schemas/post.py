from pydantic import BaseModel
from datetime import datetime


class PostListItem(BaseModel):
    id: int
    title: str
    slug: str
    website_status: str
    instagram_status: str
    created_at: datetime

    model_config = {"from_attributes": True}
