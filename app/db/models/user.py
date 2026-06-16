from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    username = Column(String(100), unique=True, nullable=False)

    password_hash = Column(String, nullable=False)

    is_admin = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
