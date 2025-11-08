"""
GraphQL types and resolvers.
"""

import strawberry
from typing import Optional
from datetime import datetime
from app.api.graphql.resolvers import asset_resolvers


@strawberry.type
class Asset:
    """GraphQL Asset type."""

    id: str
    type: str
    name: str
    region: str
    account_id: str
    tags: strawberry.scalars.JSON
    configuration: strawberry.scalars.JSON
    state: Optional[str] = None
    discovered_at: datetime
    last_seen: datetime


@strawberry.input
class AssetFilter:
    """Filter criteria for asset queries."""

    type: Optional[str] = None
    region: Optional[str] = None
    account_id: Optional[str] = None
    name_contains: Optional[str] = None
    tag_key: Optional[str] = None
    tag_value: Optional[str] = None


@strawberry.type
class DatabaseStats:
    """Database statistics."""

    total_assets: int
    total_enrichments: int
    total_relationships: int


@strawberry.type
class Query:
    """GraphQL root query."""

    @strawberry.field
    def assets(
        self, filter: Optional[AssetFilter] = None, limit: int = 100, offset: int = 0
    ) -> list[Asset]:
        """
        Query assets with optional filtering.

        Args:
            filter: Filter criteria
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            list[Asset]: List of assets
        """
        return asset_resolvers.get_assets(filter, limit, offset)

    @strawberry.field
    def asset(self, id: str) -> Optional[Asset]:
        """
        Get a single asset by ID.

        Args:
            id: Asset ID (ARN)

        Returns:
            Optional[Asset]: Asset or None if not found
        """
        return asset_resolvers.get_asset_by_id(id)

    @strawberry.field
    def stats(self) -> DatabaseStats:
        """
        Get database statistics.

        Returns:
            DatabaseStats: Current database statistics
        """
        return asset_resolvers.get_stats()
