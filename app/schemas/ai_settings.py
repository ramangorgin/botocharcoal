from pydantic import BaseModel
from typing import Optional


class AISettingsBase(BaseModel):

    provider: str
    base_url: str

    text_model: str
    image_model: str

    system_prompt: Optional[str] = None


class AISettingsCreate(AISettingsBase):

    api_key: str


class AISettingsUpdate(BaseModel):

    provider: Optional[str] = None
    base_url: Optional[str] = None

    api_key: Optional[str] = None

    text_model: Optional[str] = None
    image_model: Optional[str] = None

    system_prompt: Optional[str] = None


class AISettingsOut(AISettingsBase):

    id: int

    class Config:
        from_attributes = True
