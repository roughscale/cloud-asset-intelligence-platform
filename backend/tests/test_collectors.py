"""
Tests for AWS collectors.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.collectors.aws_config import AWSConfigCollector


class TestAWSConfigCollector:
    """Tests for AWS Config collector."""

    @patch('boto3.Session')
    def test_collector_initialization(self, mock_session_class):
        """Test collector can be initialized."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        collector = AWSConfigCollector()

        assert collector is not None
        assert collector.config_bucket is not None

    @patch('boto3.Session')
    def test_transform_config_item(self, mock_session_class, sample_config_item):
        """Test transforming AWS Config item to Asset."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        collector = AWSConfigCollector()
        asset = collector.transform(sample_config_item)

        assert asset is not None
        assert asset.type == "AWS::ECS::Service"
        assert asset.name == "api-service"
        assert asset.region == "ap-southeast-2"
        assert asset.metadata.source == "aws_config"

    @patch('boto3.Session')
    def test_transform_unknown_resource_type(self, mock_session_class):
        """Test transforming unknown resource type returns None."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        collector = AWSConfigCollector()

        config_item = {
            "resourceType": "AWS::UnknownService::UnknownResource",
            "resourceId": "unknown",
        }

        asset = collector.transform(config_item)
        assert asset is None

    @patch('boto3.Session')
    def test_collect_from_snapshot(self, mock_session_class, mock_aws_config_snapshot):
        """Test collecting assets from snapshot."""
        mock_session = MagicMock()
        mock_s3_client = MagicMock()

        # Mock S3 client methods
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "AWSLogs/123/Config/ap-southeast-2/2025/01/15/ConfigSnapshot/snapshot.json.gz",
                    "Size": 1024,
                    "LastModified": "2025-01-15T10:00:00",
                }
            ]
        }

        # Gzip the snapshot data since file ends with .gz
        import json
        import gzip
        snapshot_json = json.dumps(mock_aws_config_snapshot).encode('utf-8')
        snapshot_data = gzip.compress(snapshot_json)

        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: snapshot_data)
        }

        mock_session.client.return_value = mock_s3_client
        mock_session_class.return_value = mock_session

        collector = AWSConfigCollector()
        assets = collector.collect()

        assert len(assets) == 2  # ECS service and S3 bucket
        assert assets[0].type == "AWS::ECS::Service"
        assert assets[1].type == "AWS::S3::Bucket"
