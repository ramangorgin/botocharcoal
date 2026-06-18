# app/tasks/__init__.py
from app.tasks.celery_app import celery_app
from app.tasks import generate_post  # This ensures the task is registered

__all__ = ['celery_app', 'generate_post']
