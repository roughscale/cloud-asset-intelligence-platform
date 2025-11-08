"""Integration tests for AWS Config collection.

These tests verify the complete AWS Config collection workflow:
1. Downloading snapshots from S3
2. Parsing AWS Config format
3. Transforming to Asset models
4. Storing in Neo4j
5. Error handling and edge cases
"""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime
import json
import gzip

from app.collectors.aws_config import AWSConfigCollector
from app.services.collection_service import CollectionService
from app.models.enums import AssetType


@pytest.mark.integration
class TestAWSConfigCollectionWorkflow:
    """Test complete AWS Config collection workflow."""

    @patch('boto3.Session')
    def test_collect_multiple_resource_types(self, mock_session_class, mock_neo4j_client):
        """Test collecting various AWS resource types from Config."""
        # Create realistic AWS Config snapshot with multiple resource types
        snapshot = {
            "configurationItems": [
                {
                    "resourceType": "AWS::ECS::Service",
                    "resourceId": "arn:aws:ecs:ap-southeast-2:123:service/prod/api",
                    "resourceName": "api-service",
                    "awsRegion": "ap-southeast-2",
                    "awsAccountId": "123456789012",
                    "configurationItemCaptureTime": "2025-01-15T10:00:00.000Z",
                    "configuration": {
                        "serviceName": "api-service",
                        "desiredCount": 3,
                        "runningCount": 3,
                    },
                    "tags": {"Environment": "production", "Team": "platform"},
                    "configurationItemStatus": "OK",
                },
                {
                    "resourceType": "AWS::RDS::DBInstance",
                    "resourceId": "arn:aws:rds:ap-southeast-2:123:db:postgres-prod",
                    "resourceName": "postgres-prod",
                    "awsRegion": "ap-southeast-2",
                    "awsAccountId": "123456789012",
                    "configurationItemCaptureTime": "2025-01-15T10:00:00.000Z",
                    "configuration": {
                        "dbInstanceIdentifier": "postgres-prod",
                        "dbInstanceClass": "db.t3.medium",
                        "engine": "postgres",
                        "engineVersion": "15.4",
                    },
                    "tags": {"Environment": "production", "Database": "main"},
                    "configurationItemStatus": "OK",
                },
                {
                    "resourceType": "AWS::Lambda::Function",
                    "resourceId": "arn:aws:lambda:ap-southeast-2:123:function:data-processor",
                    "resourceName": "data-processor",
                    "awsRegion": "ap-southeast-2",
                    "awsAccountId": "123456789012",
                    "configurationItemCaptureTime": "2025-01-15T10:00:00.000Z",
                    "configuration": {
                        "functionName": "data-processor",
                        "runtime": "python3.11",
                        "memorySize": 512,
                        "timeout": 60,
                    },
                    "tags": {"Environment": "production"},
                    "configurationItemStatus": "OK",
                },
            ]
        }

        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "AWSLogs/123/Config/ap-southeast-2/2025/01/15/ConfigSnapshot/snap.json.gz",
                    "Size": 2048,
                    "LastModified": datetime(2025, 1, 15, 10, 0, 0),
                }
            ]
        }

        snapshot_data = gzip.compress(json.dumps(snapshot).encode('utf-8'))
        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: snapshot_data)
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_session_class.return_value = mock_session

        # Collect assets
        collector = AWSConfigCollector()
        assets = collector.collect()

        # Verify collected assets
        assert len(assets) == 3
        assert assets[0].type == AssetType.ECS_SERVICE
        assert assets[1].type == AssetType.RDS_INSTANCE
        assert assets[2].type == AssetType.LAMBDA_FUNCTION

        # Verify asset details
        assert assets[0].name == "api-service"
        assert assets[0].source_tags["Environment"] == "production"
        assert assets[0].configuration["desiredCount"] == 3

    @patch('boto3.Session')
    def test_collect_filters_deleted_resources(self, mock_session_class):
        """Test that deleted resources are filtered out."""
        snapshot = {
            "configurationItems": [
                {
                    "resourceType": "AWS::S3::Bucket",
                    "resourceId": "arn:aws:s3:::active-bucket",
                    "resourceName": "active-bucket",
                    "awsRegion": "ap-southeast-2",
                    "awsAccountId": "123456789012",
                    "configurationItemCaptureTime": "2025-01-15T10:00:00.000Z",
                    "configuration": {"name": "active-bucket"},
                    "tags": {},
                    "configurationItemStatus": "OK",
                },
                {
                    "resourceType": "AWS::S3::Bucket",
                    "resourceId": "arn:aws:s3:::deleted-bucket",
                    "resourceName": "deleted-bucket",
                    "awsRegion": "ap-southeast-2",
                    "awsAccountId": "123456789012",
                    "configurationItemCaptureTime": "2025-01-15T10:00:00.000Z",
                    "configuration": {},
                    "tags": {},
                    "configurationItemStatus": "ResourceDeleted",
                },
            ]
        }

        # Mock S3
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [{
                "Key": "AWSLogs/123/Config/ap-southeast-2/2025/01/15/ConfigSnapshot/snap.json.gz",
                "Size": 1024,
                "LastModified": datetime.now()
            }]
        }
        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: gzip.compress(json.dumps(snapshot).encode('utf-8')))
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_session_class.return_value = mock_session

        # Collect
        collector = AWSConfigCollector()
        assets = collector.collect()

        # Should only have the active bucket
        assert len(assets) == 1
        assert assets[0].name == "active-bucket"

    @patch('boto3.Session')
    def test_collect_handles_missing_tags(self, mock_session_class):
        """Test collecting resources without tags."""
        snapshot = {
            "configurationItems": [
                {
                    "resourceType": "AWS::EC2::Instance",
                    "resourceId": "arn:aws:ec2:ap-southeast-2:123:instance/i-123",
                    "resourceName": "instance-no-tags",
                    "awsRegion": "ap-southeast-2",
                    "awsAccountId": "123456789012",
                    "configurationItemCaptureTime": "2025-01-15T10:00:00.000Z",
                    "configuration": {"instanceType": "t3.micro"},
                    # No tags field
                    "configurationItemStatus": "OK",
                }
            ]
        }

        # Mock S3
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [{
                "Key": "AWSLogs/123/Config/ap-southeast-2/2025/01/15/ConfigSnapshot/snap.json.gz",
                "Size": 1024,
                "LastModified": datetime.now()
            }]
        }
        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: gzip.compress(json.dumps(snapshot).encode('utf-8')))
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_session_class.return_value = mock_session

        # Collect
        collector = AWSConfigCollector()
        assets = collector.collect()

        # Should handle missing tags gracefully
        assert len(assets) == 1
        assert assets[0].source_tags == {}

    @patch('boto3.Session')
    def test_collect_handles_s3_errors(self, mock_session_class):
        """Test error handling for S3 access issues."""
        from botocore.exceptions import ClientError

        # Mock S3 client that raises error
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "ListObjectsV2"
        )

        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_session_class.return_value = mock_session

        # Collect should handle error gracefully
        collector = AWSConfigCollector()
        assets = collector.collect()

        # Should return empty list on error
        assert assets == []

    @patch('boto3.Session')
    def test_collect_empty_snapshot(self, mock_session_class):
        """Test collecting from empty snapshot."""
        snapshot = {"configurationItems": []}

        # Mock S3
        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "snap.json.gz", "Size": 100, "LastModified": datetime.now()}]
        }
        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: gzip.compress(json.dumps(snapshot).encode('utf-8')))
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_session_class.return_value = mock_session

        # Collect
        collector = AWSConfigCollector()
        assets = collector.collect()

        # Should handle empty snapshot
        assert assets == []


@pytest.mark.integration
class TestCollectionServiceIntegration:
    """Test Collection Service with Neo4j integration."""

    @patch('app.services.collection_service.GraphService')
    @patch('app.services.collection_service.AWSConfigCollector')
    def test_collect_and_store_to_neo4j(self, mock_collector_class, mock_graph_service_class, sample_asset):
        """Test complete collection workflow including Neo4j storage."""
        # Mock collector to return sample assets
        mock_collector = MagicMock()
        mock_collector.collect.return_value = [sample_asset]
        mock_collector_class.return_value = mock_collector

        # Mock GraphService
        mock_graph_service = MagicMock()
        mock_graph_service.bulk_upsert_assets.return_value = {"successful": 1, "failed": 0}
        mock_graph_service_class.return_value = mock_graph_service

        # Run collection
        service = CollectionService()
        result = service.collect_from_aws_config()

        # Verify collection completed
        assert result["status"] == "completed"
        assert result["assets_collected"] == 1
        assert result["assets_ingested"] == 1
        assert result["assets_failed"] == 0

        # Verify GraphService was called to store assets
        mock_graph_service.bulk_upsert_assets.assert_called_once_with([sample_asset])

    @patch('app.services.collection_service.GraphService')
    @patch('app.services.collection_service.AWSConfigCollector')
    def test_collect_handles_neo4j_errors(self, mock_collector_class, mock_graph_service_class, sample_asset):
        """Test error handling when Neo4j storage fails."""
        # Mock collector
        mock_collector = MagicMock()
        mock_collector.collect.return_value = [sample_asset]
        mock_collector_class.return_value = mock_collector

        # Mock GraphService to report failures
        mock_graph_service = MagicMock()
        mock_graph_service.bulk_upsert_assets.return_value = {"successful": 0, "failed": 1}
        mock_graph_service_class.return_value = mock_graph_service

        # Run collection
        service = CollectionService()
        result = service.collect_from_aws_config()

        # Should track failures
        assert result["status"] == "completed"
        assert result["assets_collected"] == 1
        assert result["assets_ingested"] == 0
        assert result["assets_failed"] == 1
