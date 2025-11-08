"""
Tests for API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_healthy(self, test_client, mock_neo4j_client, mock_redis_client):
        """Test health check when all services are healthy."""
        mock_neo4j_client.verify_connectivity.return_value = True

        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert data["services"]["neo4j"] == "healthy"
        assert data["services"]["redis"] == "healthy"

    def test_health_check_degraded(self, test_client, mock_neo4j_client):
        """Test health check when Neo4j is down."""
        mock_neo4j_client.verify_connectivity.return_value = False

        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["neo4j"] == "unhealthy"


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns API information."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Asset Inventory API"
        assert data["version"] == "0.1.0"
        assert data["graphql_endpoint"] == "/graphql"


class TestStatsEndpoint:
    """Tests for stats endpoint."""

    def test_stats_endpoint(self, test_client, mock_neo4j_client):
        """Test stats endpoint."""
        mock_neo4j_client.get_stats.return_value = {
            "total_assets": 150,
            "total_enrichments": 50,
            "total_relationships": 200,
            "assets_by_type": [
                {"type": "s3_bucket", "count": 45},
                {"type": "ecs_service", "count": 30},
            ],
            "assets_by_region": [
                {"region": "ap-southeast-2", "count": 150},
            ],
        }

        response = test_client.get("/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_assets"] == 150
        assert data["total_enrichments"] == 50
        assert len(data["assets_by_type"]) == 2


class TestGraphQLEndpoint:
    """Tests for GraphQL endpoint."""

    def test_graphql_endpoint_exists(self, test_client):
        """Test GraphQL endpoint is available."""
        response = test_client.get("/graphql")
        # GraphQL playground should be accessible
        assert response.status_code == 200

    def test_graphql_query_stats(self, test_client, mock_neo4j_client):
        """Test GraphQL stats query."""
        mock_neo4j_client.get_stats.return_value = {
            "total_assets": 10,
            "total_enrichments": 5,
            "total_relationships": 15,
        }

        query = """
        query {
            stats {
                totalAssets
                totalEnrichments
                totalRelationships
            }
        }
        """

        response = test_client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["stats"]["totalAssets"] == 10

    def test_graphql_query_assets(self, test_client, mock_neo4j_client):
        """Test GraphQL assets query."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "a": {
                    "id": "arn:aws:ecs:ap-southeast-2:123:service/test",
                    "type": "ecs_service",
                    "name": "test-service",
                    "region": "ap-southeast-2",
                    "account_id": "123456789",
                    "source_tags": {"Environment": "production"},
                    "configuration": {},
                    "state": "ACTIVE",
                    "discovered_at": "2025-01-15T10:00:00",
                    "last_seen": "2025-01-15T15:00:00",
                }
            }
        ]

        query = """
        query {
            assets(limit: 10) {
                id
                type
                name
                region
            }
        }
        """

        response = test_client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]["assets"]) == 1
        assert data["data"]["assets"][0]["name"] == "test-service"


class TestCollectionEndpoints:
    """Tests for collection endpoints."""

    @patch('app.services.CollectionService')
    def test_trigger_aws_config_collection(self, mock_service_class, test_client):
        """Test triggering AWS Config collection."""
        mock_service = MagicMock()
        mock_service.collect_from_aws_config.return_value = {
            "status": "completed",
            "assets_collected": 150,
            "assets_ingested": 150,
            "assets_failed": 0,
            "duration_seconds": 12.5,
        }
        mock_service_class.return_value = mock_service

        response = test_client.post("/api/collect/aws-config")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["assets_collected"] == 150

    @patch('app.services.CollectionService')
    def test_list_snapshots(self, mock_service_class, test_client):
        """Test listing available snapshots."""
        mock_service = MagicMock()
        mock_service.list_available_snapshots.return_value = [
            {
                "key": "AWSLogs/.../snapshot1.json.gz",
                "size": 1024,
                "last_modified": "2025-01-15T10:00:00",
            }
        ]
        mock_service_class.return_value = mock_service

        response = test_client.get("/api/collect/snapshots")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "snapshot1.json.gz" in data[0]["key"]
