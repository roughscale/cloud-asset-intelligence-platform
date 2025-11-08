"""
Base collector class for asset collection.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any
import boto3
from app.config import get_settings

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Base class for all collectors."""

    def __init__(self):
        """Initialize collector with AWS session."""
        self.settings = get_settings()
        self.session = self._create_aws_session()

    def _create_aws_session(self) -> boto3.Session:
        """
        Create AWS session based on authentication strategy.

        Returns:
            boto3.Session: Configured AWS session
        """
        kwargs = self.settings.get_aws_session_kwargs()
        session = boto3.Session(**kwargs)

        # Log authentication method
        credentials = session.get_credentials()
        if credentials:
            logger.info(
                f"AWS session created successfully using {self.settings.aws_auth_strategy}"
            )
        else:
            logger.warning("AWS session created but credentials not found")

        return session

    def get_client(self, service_name: str, region: str | None = None):
        """
        Get AWS service client.

        Args:
            service_name: AWS service name (e.g., 's3', 'ec2')
            region: AWS region (defaults to configured region)

        Returns:
            boto3 client: AWS service client
        """
        region = region or self.settings.aws_region
        return self.session.client(service_name, region_name=region)

    @abstractmethod
    def collect(self) -> list[dict[str, Any]]:
        """
        Collect assets.

        Returns:
            list: List of collected assets
        """
        pass

    @abstractmethod
    def transform(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform raw AWS data to internal asset model.

        Args:
            raw_data: Raw data from AWS

        Returns:
            dict: Transformed asset data
        """
        pass
