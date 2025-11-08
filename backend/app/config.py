"""
Application configuration management.
Handles environment variables and AWS authentication strategies.
"""

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Locale and Timezone
    aws_region: str = "ap-southeast-2"
    aws_default_region: str = "ap-southeast-2"
    tz: str = "Australia/Sydney"
    locale: str = "en_AU"

    # AWS Configuration
    aws_config_bucket: str
    aws_profile: str | None = None
    aws_auth_strategy: Literal["profile", "roles_anywhere", "iam_role"] = "profile"

    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "asset-inventory-dev"
    neo4j_database: str = "neo4j"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"

    # Celery Configuration
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set Celery URLs from Redis if not explicitly set
        if not self.celery_broker_url:
            self.celery_broker_url = self.redis_url
        if not self.celery_result_backend:
            self.celery_result_backend = self.redis_url

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    def get_aws_session_kwargs(self) -> dict:
        """
        Get AWS session kwargs based on authentication strategy.

        Returns:
            dict: Keyword arguments for boto3.Session()
        """
        kwargs = {
            "region_name": self.aws_region
        }

        if self.aws_auth_strategy == "profile" and self.aws_profile:
            # Local development: use AWS CLI profile
            kwargs["profile_name"] = self.aws_profile
            logger.info(f"Using AWS profile: {self.aws_profile}")

        elif self.aws_auth_strategy == "roles_anywhere":
            # IAM Roles Anywhere: credentials will be set via environment
            # This is handled by AWS SDK automatically when credentials are in environment
            logger.info("Using IAM Roles Anywhere authentication")

        elif self.aws_auth_strategy == "iam_role":
            # EC2/ECS/Lambda: use instance metadata
            # boto3 will automatically use instance role
            logger.info("Using IAM role from instance metadata")

        return kwargs


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Convenience accessor
settings = get_settings()
