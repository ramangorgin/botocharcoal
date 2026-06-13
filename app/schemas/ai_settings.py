from pydantic import BaseModel, Field
from datetime import datetime


class AISettingsCreateSchema(BaseModel):
    provider: str = Field(default="openai", pattern="^(openai|anthropic|custom)$")
    api_key: str | None = Field(None, max_length=512)
    api_base_url: str | None = Field(None, max_length=512)
    text_model: str | None = Field(None, max_length=128)
    image_model: str | None = Field(None, max_length=128)
    prompt_template: str | None = Field(None, max_length=8192)


class AISettingsResponseSchema(BaseModel):
    id: int
    provider: str
    api_key: str | None
    api_base_url: str | None
    text_model: str | None
    image_model: str | None
    image_size: str | None = None
    prompt_template: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
