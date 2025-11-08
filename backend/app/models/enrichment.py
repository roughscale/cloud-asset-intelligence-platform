"""
Enrichment data models for user-managed asset metadata.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field
from app.models.enums import (
    EnrichmentStatus,
    EnrichmentMethod,
    RelationshipType,
)


class EnrichmentMetadata(BaseModel):
    """Metadata about the enrichment itself."""

    created_by: str | None = Field(
        default=None, description="User who created the enrichment"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_by: str | None = Field(
        default=None, description="User who last updated the enrichment"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    enrichment_method: EnrichmentMethod = Field(
        default=EnrichmentMethod.MANUAL,
        description="How enrichment was created",
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1) for automated enrichments",
    )
    verified: bool = Field(
        default=False, description="Whether enrichment has been verified by a human"
    )
    notes: str | None = Field(
        default=None, description="Free-form notes about the enrichment"
    )
    rule_name: str | None = Field(
        default=None, description="Name of rule that generated this (if rule-based)"
    )


class CustomRelationship(BaseModel):
    """Custom relationship not derived from AWS infrastructure."""

    type: str = Field(description="Relationship type (can be custom string)")
    target: str = Field(
        description="Target identifier (asset ARN, team name, app name, etc.)"
    )
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Additional properties"
    )


class Enrichment(BaseModel):
    """
    User-managed enrichment data for an asset.
    This is mutable and separate from the source asset data.
    """

    # Identity
    enrichment_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique enrichment ID"
    )
    asset_id: str = Field(description="ARN of the asset being enriched")

    # Local classification tags (can override source tags)
    local_tags: dict[str, str] = Field(
        default_factory=dict,
        description="Local classification tags managed by users",
    )

    # Custom attributes (beyond tags)
    custom_attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom attributes like owner emails, URLs, etc.",
    )

    # Custom relationships not in AWS
    custom_relationships: list[CustomRelationship] = Field(
        default_factory=list,
        description="Business and logical relationships",
    )

    # Metadata about the enrichment
    enrichment_metadata: EnrichmentMetadata = Field(
        default_factory=EnrichmentMetadata,
        description="Metadata about this enrichment",
    )

    # Tag conflict resolution
    override_source_tags: list[str] = Field(
        default_factory=list,
        description="List of source tag keys that local tags should override",
    )

    # Lifecycle
    status: EnrichmentStatus = Field(
        default=EnrichmentStatus.ACTIVE, description="Enrichment status"
    )
    version: int = Field(default=1, description="Version number for history tracking")

    # Export tracking
    exported_to_aws: bool = Field(
        default=False, description="Whether enrichment has been exported to AWS tags"
    )
    last_export_date: datetime | None = Field(
        default=None, description="Last time enrichment was exported to AWS"
    )
    exported_tags: list[str] = Field(
        default_factory=list, description="List of tag keys that were exported"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enrichment_id": "550e8400-e29b-41d4-a716-446655440000",
                "asset_id": "arn:aws:ecs:ap-southeast-2:123:service/prod/api",
                "local_tags": {
                    "Owner": "platform-team@company.com",
                    "CostCenter": "engineering-core",
                    "Criticality": "tier-1",
                    "DataClassification": "pii",
                    "ComplianceScope": "sox,pci-dss",
                },
                "custom_attributes": {
                    "business_owner": "jane.doe@company.com",
                    "technical_owner": "john.smith@company.com",
                    "runbook_url": "https://wiki.company.com/runbooks/api-service",
                    "oncall_rotation": "platform-oncall",
                    "estimated_monthly_cost": 1500.00,
                },
                "custom_relationships": [
                    {
                        "type": "SUPPORTS_APPLICATION",
                        "target": "mobile-app-v2",
                        "properties": {"criticality": "high"},
                    },
                    {
                        "type": "OWNED_BY_TEAM",
                        "target": "team:platform",
                        "properties": {},
                    },
                ],
                "enrichment_metadata": {
                    "created_by": "user@company.com",
                    "created_at": "2025-01-15T10:00:00Z",
                    "updated_by": "user@company.com",
                    "updated_at": "2025-01-15T12:00:00Z",
                    "enrichment_method": "manual",
                    "confidence_score": 1.0,
                    "verified": True,
                    "notes": "Confirmed with team lead",
                },
                "override_source_tags": ["Environment"],
                "status": "active",
                "version": 2,
                "exported_to_aws": False,
            }
        }


class EnrichmentHistory(BaseModel):
    """Historical version of an enrichment."""

    enrichment_id: str
    asset_id: str
    version: int
    changed_fields: list[str] = Field(
        default_factory=list, description="Fields that changed in this version"
    )
    changed_by: str | None = None
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    change_reason: str | None = Field(
        default=None, description="Reason for the change"
    )
    previous_data: dict[str, Any] = Field(
        default_factory=dict, description="Previous values of changed fields"
    )
