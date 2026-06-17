# app/tasks/celery_app.py
from celery import Celery

celery_app = Celery(
    "tasks",
    broker="pyamqp://guest@localhost//",
    backend="rpc://",
    include=["app.tasks.generate_post"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tehran",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 دقیقه timeout
)
