# app/db/models/job.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)

    # اطلاعات اصلی درخواست
    topic = Column(String(255), nullable=False)
    image_instructions = Column(Text)  # دستورالعمل‌های اضافی برای مدل تصویر
    text_instructions = Column(Text)   # دستورالعمل‌های اضافی برای مدل متنی
    blog_image_count = Column(Integer, default=1)  # تعداد تصویر برای بلاگ
    instagram_image_count = Column(Integer, default=1)  # تعداد تصویر برای اینستاگرام
    auto_publish = Column(Boolean, default=False)  # آیا به طور خودکار در بلاگ پابلیش شود؟

    # وضعیت و نتایج
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)  # پست ایجاد شده
    error_message = Column(Text, nullable=True)

    # متادیتا
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # رابطه‌ها
    post = relationship("Post", backref="job")

    def __repr__(self):
        return f"<Job(id={self.id}, topic='{self.topic}', status='{self.status}')>"
