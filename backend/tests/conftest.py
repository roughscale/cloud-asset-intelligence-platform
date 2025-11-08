"""
Pytest configuration and fixtures for backend tests.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient

# Import app components
from app.models.asset import Asset, AssetMetadata
from app.models.enrichment import Enrichment, EnrichmentMetadata
from app.models.enums import AssetType, EnrichmentStatus, EnrichmentMethod


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client for testing."""
    mock_client = MagicMock()
    mock_client.verify_connectivity.return_value = True
    mock_client.execute_query.return_value = []
    mock_client.execute_write.return_value = []
    mock_client.get_stats.return_value = {
        "total_assets": 0,
        "total_enrichments": 0,
        "total_relationships": 0,
    }
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = MagicMock()
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.exists.return_value = 0
    return mock_client


@pytest.fixture
def sample_asset():
    """Sample asset for testing."""
    metadata = AssetMetadata(
        source="aws_config",
        discovered_at=datetime(2025, 1, 15, 10, 0, 0),
        last_seen=datetime(2025, 1, 15, 15, 30, 0),
        last_modified=datetime(2025, 1, 10, 8, 0, 0),
    )

    return Asset(
        id="arn:aws:ecs:ap-southeast-2:123456789:service/prod-cluster/api-service",
        type=AssetType.ECS_SERVICE,
        name="api-service",
        region="ap-southeast-2",
        account_id="123456789",
        source_tags={
            "Name": "api-service",
            "Environment": "production",
        },
        configuration={
            "serviceName": "api-service",
            "desiredCount": 3,
            "launchType": "FARGATE",
        },
        metadata=metadata,
        state="ACTIVE",
    )


@pytest.fixture
def sample_enrichment():
    """Sample enrichment for testing."""
    metadata = EnrichmentMetadata(
        created_by="test-user@company.com",
        enrichment_method=EnrichmentMethod.MANUAL,
        confidence_score=1.0,
        verified=True,
    )

    return Enrichment(
        enrichment_id="test-enrichment-123",
        asset_id="arn:aws:ecs:ap-southeast-2:123456789:service/prod-cluster/api-service",
        local_tags={
            "Owner": "platform-team@company.com",
            "CostCenter": "engineering-core",
            "Criticality": "tier-1",
        },
        custom_attributes={
            "business_owner": "jane.doe@company.com",
            "technical_owner": "john.smith@company.com",
            "runbook_url": "https://wiki.company.com/runbooks/api-service",
        },
        enrichment_metadata=metadata,
        status=EnrichmentStatus.ACTIVE,
    )


@pytest.fixture
def sample_config_item():
    """Sample AWS Config configuration item."""
    return {
        "resourceType": "AWS::ECS::Service",
        "resourceId": "api-service",
        "resourceName": "api-service",
        "ARN": "arn:aws:ecs:ap-southeast-2:123456789:service/prod-cluster/api-service",
        "awsRegion": "ap-southeast-2",
        "awsAccountId": "123456789",
        "configurationItemCaptureTime": "2025-01-15T10:00:00Z",
        "configurationItemStatus": "OK",
        "tags": {
            "Name": "api-service",
            "Environment": "production",
        },
        "configuration": {
            "serviceName": "api-service",
            "desiredCount": 3,
            "launchType": "FARGATE",
        },
    }


@pytest.fixture
def mock_aws_config_snapshot():
    """Mock AWS Config snapshot data."""
    return {
        "configurationItems": [
            {
                "resourceType": "AWS::ECS::Service",
                "resourceId": "api-service",
                "resourceName": "api-service",
                "ARN": "arn:aws:ecs:ap-southeast-2:123:service/prod/api",
                "awsRegion": "ap-southeast-2",
                "awsAccountId": "123456789",
                "configurationItemCaptureTime": "2025-01-15T10:00:00Z",
                "tags": {"Environment": "production"},
                "configuration": {"desiredCount": 3},
            },
            {
                "resourceType": "AWS::S3::Bucket",
                "resourceId": "my-test-bucket",
                "resourceName": "my-test-bucket",
                "ARN": "arn:aws:s3:::my-test-bucket",
                "awsRegion": "ap-southeast-2",
                "awsAccountId": "123456789",
                "configurationItemCaptureTime": "2025-01-15T10:00:00Z",
                "tags": {},
                "configuration": {"Name": "my-test-bucket"},
            },
        ]
    }


@pytest.fixture
def test_client(monkeypatch, mock_neo4j_client, mock_redis_client):
    """FastAPI test client with mocked dependencies."""
    # Mock the database clients
    monkeypatch.setattr("app.db.neo4j_client._neo4j_client", mock_neo4j_client)
    monkeypatch.setattr("app.db.redis_client._redis_client", mock_redis_client)

    # Import after mocking
    from app.main import app

    return TestClient(app)


@pytest.fixture
def mock_boto3_session():
    """Mock boto3 session for AWS API testing."""
    mock_session = MagicMock()
    mock_client = MagicMock()

    # Mock S3 client responses
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {
                "Key": "AWSLogs/123456789/Config/ap-southeast-2/2025/01/15/ConfigSnapshot/snapshot.json.gz",
                "Size": 1024,
                "LastModified": datetime(2025, 1, 15, 10, 0, 0),
            }
        ]
    }

    mock_session.client.return_value = mock_client
    return mock_session


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    import app.db.neo4j_client as neo4j_module
    import app.db.redis_client as redis_module

    yield

    # Reset singletons after each test
    neo4j_module._neo4j_client = None
    redis_module._redis_client = None


@pytest.fixture
def temp_env_vars(monkeypatch):
    """Set temporary environment variables for testing."""
    monkeypatch.setenv("AWS_REGION", "ap-southeast-2")
    monkeypatch.setenv("AWS_CONFIG_BUCKET", "test-config-bucket")
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    monkeypatch.setenv("ENVIRONMENT", "development")
