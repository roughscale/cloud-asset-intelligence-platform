"""Tests for Celery application configuration."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestCeleryApp:
    """Tests for Celery app configuration."""

    def test_celery_app_exists(self):
        """Test that celery app can be imported."""
        from app.tasks.celery_app import celery_app

        assert celery_app is not None
        assert celery_app.main == "asset_inventory"

    def test_celery_app_configuration(self):
        """Test that celery app has correct configuration."""
        from app.tasks.celery_app import celery_app

        # Check serialization settings
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

        # Check timezone
        assert celery_app.conf.timezone == "Australia/Sydney"
        assert celery_app.conf.enable_utc is True

    def test_celery_app_uses_redis_broker(self):
        """Test that celery app uses Redis as broker."""
        from app.tasks.celery_app import celery_app

        # Broker should be configured
        assert celery_app.conf.broker_url is not None
        assert "redis" in celery_app.conf.broker_url

    def test_celery_app_task_time_limits(self):
        """Test that celery app has reasonable task time limits."""
        from app.tasks.celery_app import celery_app

        # Should have time limits configured
        assert celery_app.conf.task_time_limit is not None
        assert celery_app.conf.task_soft_time_limit is not None

        # Soft limit should be less than hard limit
        assert celery_app.conf.task_soft_time_limit < celery_app.conf.task_time_limit


@pytest.mark.unit
class TestCollectionTasks:
    """Tests for collection tasks."""

    @patch('app.tasks.collection_tasks.CollectionService')
    def test_collect_aws_config_task_exists(self, mock_service):
        """Test that AWS Config collection task can be imported."""
        from app.tasks.collection_tasks import collect_aws_config

        assert collect_aws_config is not None
        assert callable(collect_aws_config)

    @patch('app.tasks.collection_tasks.CollectionService')
    def test_collect_aws_config_task_calls_service(self, mock_service):
        """Test that task calls the collection service."""
        from app.tasks.collection_tasks import collect_aws_config

        # Mock the service
        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        mock_instance.collect_from_aws_config.return_value = {
            "status": "success",
            "assets_collected": 10
        }

        # Call the task
        result = collect_aws_config(s3_key="test-snapshot.json")

        # Verify service was called
        mock_service.assert_called_once()
        mock_instance.collect_from_aws_config.assert_called_once_with("test-snapshot.json")

        # Verify result
        assert result["status"] == "success"
        assert result["assets_collected"] == 10
