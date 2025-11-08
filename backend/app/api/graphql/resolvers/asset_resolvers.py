"""
Asset query resolvers for GraphQL.
"""

import logging
from typing import Optional
from datetime import datetime
from app.db import get_neo4j_client

logger = logging.getLogger(__name__)


def get_assets(filter_input, limit: int = 100, offset: int = 0) -> list:
    """
    Get assets with optional filtering.

    Args:
        filter_input: Filter criteria
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        list: List of asset dictionaries
    """
    neo4j = get_neo4j_client()

    # Build Cypher query
    where_clauses = []
    parameters = {"limit": limit, "offset": offset}

    if filter_input:
        if filter_input.type:
            where_clauses.append("a.type = $type")
            parameters["type"] = filter_input.type

        if filter_input.region:
            where_clauses.append("a.region = $region")
            parameters["region"] = filter_input.region

        if filter_input.account_id:
            where_clauses.append("a.account_id = $account_id")
            parameters["account_id"] = filter_input.account_id

        if filter_input.name_contains:
            where_clauses.append("a.name CONTAINS $name_contains")
            parameters["name_contains"] = filter_input.name_contains

    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"""
        MATCH (a:Asset)
        {where_clause}
        RETURN a
        ORDER BY a.last_seen DESC
        SKIP $offset
        LIMIT $limit
    """

    try:
        results = neo4j.execute_query(query, parameters)
        assets = []

        for record in results:
            asset_data = record["a"]
            assets.append(_format_asset(asset_data))

        return assets
    except Exception as e:
        logger.error(f"Error querying assets: {e}")
        return []


def get_asset_by_id(asset_id: str) -> Optional[dict]:
    """
    Get a single asset by ID.

    Args:
        asset_id: Asset ID (ARN)

    Returns:
        Optional[dict]: Asset data or None if not found
    """
    neo4j = get_neo4j_client()

    query = """
        MATCH (a:Asset {id: $asset_id})
        RETURN a
    """

    try:
        results = neo4j.execute_query(query, {"asset_id": asset_id})
        if results:
            return _format_asset(results[0]["a"])
        return None
    except Exception as e:
        logger.error(f"Error getting asset {asset_id}: {e}")
        return None


def get_stats() -> dict:
    """
    Get database statistics.

    Returns:
        dict: Database statistics
    """
    neo4j = get_neo4j_client()
    stats = neo4j.get_stats()

    return {
        "total_assets": stats.get("total_assets", 0),
        "total_enrichments": stats.get("total_enrichments", 0),
        "total_relationships": stats.get("total_relationships", 0),
    }


def _format_asset(asset_data: dict) -> dict:
    """
    Format asset data for GraphQL response.

    Args:
        asset_data: Raw asset data from Neo4j

    Returns:
        dict: Formatted asset data
    """
    # Ensure datetime fields are datetime objects
    discovered_at = asset_data.get("discovered_at")
    last_seen = asset_data.get("last_seen")

    if isinstance(discovered_at, str):
        discovered_at = datetime.fromisoformat(discovered_at)
    if isinstance(last_seen, str):
        last_seen = datetime.fromisoformat(last_seen)

    return {
        "id": asset_data.get("id"),
        "type": asset_data.get("type"),
        "name": asset_data.get("name"),
        "region": asset_data.get("region"),
        "account_id": asset_data.get("account_id"),
        "tags": asset_data.get("source_tags", {}),
        "configuration": asset_data.get("configuration", {}),
        "state": asset_data.get("state"),
        "discovered_at": discovered_at or datetime.utcnow(),
        "last_seen": last_seen or datetime.utcnow(),
    }
