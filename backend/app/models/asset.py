"""
Asset data models representing AWS resources.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
from app.models.enums import AssetType, RelationshipType


class AssetMetadata(BaseModel):
    """Metadata about asset collection and lifecycle."""

    source: str = Field(description="Data source (e.g., 'aws_config', 'direct_api')")
    discovered_at: datetime = Field(description="When asset was first discovered")
    last_seen: datetime = Field(description="Last time asset was observed")
    last_modified: datetime | None = Field(
        default=None, description="Last modification time from AWS"
    )
    collector_version: str | None = Field(
        default=None, description="Version of collector that captured this data"
    )
    config_snapshot_time: datetime | None = Field(
        default=None, description="AWS Config snapshot timestamp"
    )


class Asset(BaseModel):
    """
    Core asset model representing an AWS resource.
    This is the immutable "source of truth" from AWS.
    """

    # Identity
    id: str = Field(description="Unique identifier (typically ARN)")
    type: AssetType = Field(description="Asset type classification")
    name: str = Field(description="Human-readable resource name")

    # AWS Context
    region: str = Field(description="AWS region (e.g., 'ap-southeast-2')")
    account_id: str = Field(description="AWS account ID")
    availability_zone: str | None = Field(
        default=None, description="Availability zone if applicable"
    )

    # Tags from AWS (immutable source tags)
    source_tags: dict[str, str] = Field(
        default_factory=dict, description="Tags from AWS (read-only)"
    )

    # Resource configuration from AWS
    configuration: dict[str, Any] = Field(
        default_factory=dict,
        description="Full configuration from AWS Config or API",
    )

    # Metadata
    metadata: AssetMetadata = Field(description="Collection metadata")

    # Optional fields
    description: str | None = Field(
        default=None, description="Resource description if available"
    )
    state: str | None = Field(
        default=None, description="Resource state (e.g., 'running', 'available')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "arn:aws:ecs:ap-southeast-2:123456789:service/prod-cluster/api-service",
                "type": "ecs_service",
                "name": "api-service",
                "region": "ap-southeast-2",
                "account_id": "123456789",
                "source_tags": {
                    "Name": "api-service",
                    "Environment": "production",
                },
                "configuration": {
                    "serviceName": "api-service",
                    "desiredCount": 3,
                    "launchType": "FARGATE",
                },
                "metadata": {
                    "source": "aws_config",
                    "discovered_at": "2025-01-15T10:00:00Z",
                    "last_seen": "2025-01-15T15:30:00Z",
                },
                "state": "ACTIVE",
            }
        }


class AssetRelationship(BaseModel):
    """Represents a relationship between two assets."""

    source_id: str = Field(description="Source asset ID (ARN)")
    target_id: str = Field(description="Target asset ID (ARN)")
    relationship_type: RelationshipType = Field(description="Type of relationship")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional relationship properties",
    )
    discovered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When relationship was discovered",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source_id": "arn:aws:ecs:ap-southeast-2:123:service/prod/api",
                "target_id": "arn:aws:rds:ap-southeast-2:123:db:prod-db",
                "relationship_type": "USES",
                "properties": {"connection_type": "jdbc"},
                "discovered_at": "2025-01-15T10:00:00Z",
            }
        }


class MergedAsset(BaseModel):
    """
    Asset with enrichment data merged in.
    This is what gets returned to API consumers.
    """

    # Core asset data
    id: str
    type: AssetType
    name: str
    region: str
    account_id: str

    # Merged tags (source + enrichment)
    tags: dict[str, str] = Field(
        description="Merged tags from AWS and local enrichment"
    )

    # Custom attributes from enrichment
    custom_attributes: dict[str, Any] = Field(
        default_factory=dict, description="Custom attributes from enrichment"
    )

    # Original configuration
    configuration: dict[str, Any] = Field(default_factory=dict)

    # Relationships
    relationships: list[AssetRelationship] = Field(
        default_factory=list, description="Asset relationships"
    )

    # Data lineage (tracks source of data)
    data_lineage: dict[str, Any] = Field(
        default_factory=dict,
        description="Information about data sources and enrichment",
    )

    # State
    state: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "arn:aws:ecs:ap-southeast-2:123:service/prod/api",
                "type": "ecs_service",
                "name": "api-service",
                "region": "ap-southeast-2",
                "account_id": "123456789",
                "tags": {
                    "Name": "api-service",
                    "Environment": "production",
                    "Team": "platform",  # From enrichment
                    "Owner": "platform@company.com",  # From enrichment
                },
                "custom_attributes": {
                    "business_owner": "jane.doe@company.com",
                    "runbook_url": "https://wiki/runbooks/api-service",
                },
                "configuration": {"desiredCount": 3},
                "data_lineage": {
                    "source": "aws_config",
                    "enrichment_applied": True,
                    "enrichment_updated": "2025-01-15T12:00:00Z",
                },
                "relationships": [],
                "state": "ACTIVE",
            }
        }
