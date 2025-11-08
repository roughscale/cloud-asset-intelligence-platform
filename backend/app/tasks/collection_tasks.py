"""Celery tasks for asset collection."""

import logging
from typing import Any

from app.tasks.celery_app import celery_app
from app.services.collection_service import CollectionService

logger = logging.getLogger(__name__)


@celery_app.task(name="collect_aws_config", bind=True)
def collect_aws_config(self, s3_key: str | None = None) -> dict[str, Any]:
    """
    Collect assets from AWS Config.

    Args:
        s3_key: Optional S3 key for specific snapshot

    Returns:
        Dictionary with collection results
    """
    logger.info(f"Starting AWS Config collection task (s3_key: {s3_key})")

    try:
        service = CollectionService()
        result = service.collect_from_aws_config(s3_key)

        logger.info(f"AWS Config collection completed: {result}")
        return result

    except Exception as e:
        logger.error(f"AWS Config collection failed: {str(e)}", exc_info=True)
        raise
