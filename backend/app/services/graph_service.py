"""
Graph database service for asset and enrichment operations.
"""

import json
import logging
from datetime import datetime
from typing import Any
from app.db import get_neo4j_client
from app.models.asset import Asset, AssetRelationship
from app.models.enrichment import Enrichment
from app.models.enums import RelationshipType

logger = logging.getLogger(__name__)


class GraphService:
    """Service for graph database operations."""

    def __init__(self):
        """Initialize graph service."""
        self.neo4j = get_neo4j_client()

    def upsert_asset(self, asset: Asset) -> bool:
        """
        Create or update an asset in the graph database.

        Args:
            asset: Asset to upsert

        Returns:
            bool: True if successful
        """
        try:
            query = """
                MERGE (a:Asset {id: $id})
                SET a.type = $type,
                    a.name = $name,
                    a.region = $region,
                    a.account_id = $account_id,
                    a.availability_zone = $availability_zone,
                    a.source_tags = $source_tags,
                    a.configuration = $configuration,
                    a.state = $state,
                    a.description = $description,
                    a.discovered_at = COALESCE(a.discovered_at, $discovered_at),
                    a.last_seen = $last_seen,
                    a.last_modified = $last_modified,
                    a.source = $source,
                    a.config_snapshot_time = $config_snapshot_time
                RETURN a.id as id
            """

            parameters = {
                "id": asset.id,
                "type": asset.type,
                "name": asset.name,
                "region": asset.region,
                "account_id": asset.account_id,
                "availability_zone": asset.availability_zone,
                "source_tags": json.dumps(asset.source_tags),  # Serialize as JSON string
                "configuration": json.dumps(asset.configuration),  # Serialize as JSON string
                "state": asset.state,
                "description": asset.description,
                "discovered_at": asset.metadata.discovered_at.isoformat(),
                "last_seen": asset.metadata.last_seen.isoformat(),
                "last_modified": asset.metadata.last_modified.isoformat()
                if asset.metadata.last_modified
                else None,
                "source": asset.metadata.source,
                "config_snapshot_time": asset.metadata.config_snapshot_time.isoformat()
                if asset.metadata.config_snapshot_time
                else None,
            }

            result = self.neo4j.execute_write(query, parameters)

            if result:
                logger.debug(f"Upserted asset: {asset.id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error upserting asset {asset.id}: {e}")
            return False

    def bulk_upsert_assets(self, assets: list[Asset]) -> dict[str, int]:
        """
        Bulk upsert multiple assets.

        Args:
            assets: List of assets to upsert

        Returns:
            dict: Statistics (successful, failed)
        """
        stats = {"successful": 0, "failed": 0}

        for asset in assets:
            if self.upsert_asset(asset):
                stats["successful"] += 1
            else:
                stats["failed"] += 1

        logger.info(
            f"Bulk upsert complete: {stats['successful']} successful, {stats['failed']} failed"
        )
        return stats

    def create_relationship(self, relationship: AssetRelationship) -> bool:
        """
        Create a relationship between two assets.

        Args:
            relationship: Relationship to create

        Returns:
            bool: True if successful
        """
        try:
            # Note: Using APOC for dynamic relationship types would be better,
            # but for Phase 1, we'll use a generic RELATES_TO type

            query = """
                MATCH (source:Asset {id: $source_id})
                MATCH (target:Asset {id: $target_id})
                MERGE (source)-[r:RELATES_TO {type: $rel_type}]->(target)
                SET r.properties = $properties,
                    r.discovered_at = $discovered_at
                RETURN r
            """

            parameters = {
                "source_id": relationship.source_id,
                "target_id": relationship.target_id,
                "rel_type": relationship.relationship_type.value,
                "properties": relationship.properties,
                "discovered_at": relationship.discovered_at.isoformat(),
            }

            result = self.neo4j.execute_write(query, parameters)
            return bool(result)

        except Exception as e:
            logger.error(
                f"Error creating relationship {relationship.source_id} -> {relationship.target_id}: {e}"
            )
            return False

    def get_asset_by_id(self, asset_id: str) -> dict | None:
        """
        Get an asset by ID.

        Args:
            asset_id: Asset ID (ARN)

        Returns:
            dict | None: Asset data or None if not found
        """
        query = """
            MATCH (a:Asset {id: $asset_id})
            RETURN a
        """

        try:
            results = self.neo4j.execute_query(query, {"asset_id": asset_id})
            if results:
                return results[0]["a"]
            return None
        except Exception as e:
            logger.error(f"Error getting asset {asset_id}: {e}")
            return None

    def get_assets_by_type(self, asset_type: str, limit: int = 100) -> list[dict]:
        """
        Get assets by type.

        Args:
            asset_type: Asset type
            limit: Maximum number of results

        Returns:
            list[dict]: List of assets
        """
        query = """
            MATCH (a:Asset {type: $asset_type})
            RETURN a
            ORDER BY a.last_seen DESC
            LIMIT $limit
        """

        try:
            results = self.neo4j.execute_query(
                query, {"asset_type": asset_type, "limit": limit}
            )
            return [record["a"] for record in results]
        except Exception as e:
            logger.error(f"Error getting assets by type {asset_type}: {e}")
            return []

    def get_assets_by_account(self, account_id: str, limit: int = 100) -> list[dict]:
        """
        Get assets by AWS account.

        Args:
            account_id: AWS account ID
            limit: Maximum number of results

        Returns:
            list[dict]: List of assets
        """
        query = """
            MATCH (a:Asset {account_id: $account_id})
            RETURN a
            ORDER BY a.last_seen DESC
            LIMIT $limit
        """

        try:
            results = self.neo4j.execute_query(
                query, {"account_id": account_id, "limit": limit}
            )
            return [record["a"] for record in results]
        except Exception as e:
            logger.error(f"Error getting assets for account {account_id}: {e}")
            return []

    def delete_asset(self, asset_id: str) -> bool:
        """
        Delete an asset and all its relationships.

        Args:
            asset_id: Asset ID (ARN)

        Returns:
            bool: True if successful
        """
        query = """
            MATCH (a:Asset {id: $asset_id})
            DETACH DELETE a
        """

        try:
            self.neo4j.execute_write(query, {"asset_id": asset_id})
            logger.info(f"Deleted asset: {asset_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting asset {asset_id}: {e}")
            return False
