"""
Tests for data models.
"""

import pytest
from datetime import datetime
from app.models.asset import Asset, AssetMetadata
from app.models.enrichment import Enrichment, EnrichmentMetadata


class TestAssetModel:
    """Tests for Asset model."""

    def test_create_asset(self, sample_asset):
        """Test creating an asset."""
        assert sample_asset.id.startswith("arn:aws:ecs:")
        assert sample_asset.type == "AWS::ECS::Service"
        assert sample_asset.name == "api-service"
        assert sample_asset.region == "ap-southeast-2"
        assert sample_asset.account_id == "123456789"

    def test_asset_metadata(self, sample_asset):
        """Test asset metadata."""
        assert sample_asset.metadata.source == "aws_config"
        assert isinstance(sample_asset.metadata.discovered_at, datetime)
        assert isinstance(sample_asset.metadata.last_seen, datetime)

    def test_asset_tags(self, sample_asset):
        """Test asset tags."""
        assert "Name" in sample_asset.source_tags
        assert sample_asset.source_tags["Name"] == "api-service"
        assert sample_asset.source_tags["Environment"] == "production"

    def test_asset_configuration(self, sample_asset):
        """Test asset configuration."""
        assert sample_asset.configuration["serviceName"] == "api-service"
        assert sample_asset.configuration["desiredCount"] == 3
        assert sample_asset.configuration["launchType"] == "FARGATE"

    def test_asset_json_serialization(self, sample_asset):
        """Test asset can be serialized to JSON."""
        json_data = sample_asset.model_dump()
        assert json_data["type"] == "ecs_service"
        assert json_data["name"] == "api-service"


class TestEnrichmentModel:
    """Tests for Enrichment model."""

    def test_create_enrichment(self, sample_enrichment):
        """Test creating an enrichment."""
        assert sample_enrichment.enrichment_id == "test-enrichment-123"
        assert sample_enrichment.asset_id.startswith("arn:aws:ecs:")
        assert sample_enrichment.status == EnrichmentStatus.ACTIVE

    def test_enrichment_local_tags(self, sample_enrichment):
        """Test enrichment local tags."""
        assert "Owner" in sample_enrichment.local_tags
        assert sample_enrichment.local_tags["Owner"] == "platform-team@company.com"
        assert sample_enrichment.local_tags["Criticality"] == "tier-1"

    def test_enrichment_custom_attributes(self, sample_enrichment):
        """Test enrichment custom attributes."""
        assert "business_owner" in sample_enrichment.custom_attributes
        assert sample_enrichment.custom_attributes["business_owner"] == "jane.doe@company.com"

    def test_enrichment_metadata(self, sample_enrichment):
        """Test enrichment metadata."""
        assert sample_enrichment.enrichment_metadata.created_by == "test-user@company.com"
        assert sample_enrichment.enrichment_metadata.enrichment_method == EnrichmentMethod.MANUAL
        assert sample_enrichment.enrichment_metadata.confidence_score == 1.0
        assert sample_enrichment.enrichment_metadata.verified is True

    def test_enrichment_defaults(self):
        """Test enrichment default values."""
        enrichment = Enrichment(
            asset_id="arn:aws:test"
        )
        assert enrichment.status == EnrichmentStatus.ACTIVE
        assert enrichment.version == 1
        assert enrichment.exported_to_aws is False
        assert len(enrichment.enrichment_id) > 0  # UUID generated
