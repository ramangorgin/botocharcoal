from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.db.base import Base


class AISettings(Base):
    __tablename__ = "ai_settings"

    id = Column(Integer, primary_key=True)

    provider = Column(String(50), nullable=False)
    base_url = Column(Text, nullable=False)
    api_key = Column(Text, nullable=False)

    text_model = Column(String(100), nullable=False)
    image_model = Column(String(100), nullable=False)

    system_prompt = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
