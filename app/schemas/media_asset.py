from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MediaAssetOut(BaseModel):

    id: int

    role: str

    public_url: Optional[str] = None

    width: Optional[int] = None
    height: Optional[int] = None

    created_at: datetime

    class Config:
        from_attributes = True
