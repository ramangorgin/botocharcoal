from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    # رابطه برگشتی به پست‌ها
    posts = relationship("Post", secondary="post_categories", back_populates="categories")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"
