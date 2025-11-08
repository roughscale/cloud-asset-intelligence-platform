"""Celery tasks module."""

from app.tasks.celery_app import celery_app
from app.tasks.collection_tasks import collect_aws_config

__all__ = [
    "celery_app",
    "collect_aws_config",
]
