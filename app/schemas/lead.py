import re
from pydantic import BaseModel, field_validator, Field


class LeadCreateSchema(BaseModel):
    name: str | None = Field(None, max_length=128)
    phone: str = Field(..., min_length=7, max_length=32)
    city: str | None = Field(None, max_length=128)
    message: str | None = Field(None, max_length=1000)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+98|0098|0)?9\d{9}$|^\+?\d{7,15}$", cleaned):
            raise ValueError("شماره تلفن معتبر نیست")
        return cleaned
