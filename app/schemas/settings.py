from pydantic import BaseModel


class HealthStatus(BaseModel):
    database: bool
    redis: bool
    media_writable: bool
    openai_key_set: bool
    text_model_set: bool
    image_model_set: bool
    instagram_token_set: bool
    instagram_account_set: bool
