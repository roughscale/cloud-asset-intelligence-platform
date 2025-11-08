"""
Collection service for orchestrating asset collection.
"""

import logging
from datetime import datetime
from app.collectors.aws_config import AWSConfigCollector
from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)


class CollectionService:
    """Service for orchestrating asset collection and ingestion."""

    def __init__(self):
        """Initialize collection service."""
        self.graph_service = GraphService()
        self.aws_config_collector = AWSConfigCollector()

    def collect_from_aws_config(self, s3_key: str | None = None) -> dict:
        """
        Collect assets from AWS Config and ingest into graph database.

        Args:
            s3_key: Specific S3 key to process. If None, processes latest snapshot.

        Returns:
            dict: Collection statistics
        """
        logger.info("Starting AWS Config collection")
        start_time = datetime.utcnow()

        try:
            # Collect assets from AWS Config
            assets = self.aws_config_collector.collect(s3_key)

            if not assets:
                logger.warning("No assets collected from AWS Config")
                return {
                    "status": "completed",
                    "assets_collected": 0,
                    "assets_ingested": 0,
                    "duration_seconds": 0,
                    "errors": ["No assets found in snapshot"],
                }

            # Ingest assets into graph database
            logger.info(f"Ingesting {len(assets)} assets into graph database")
            ingest_stats = self.graph_service.bulk_upsert_assets(assets)

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Build response
            result = {
                "status": "completed",
                "assets_collected": len(assets),
                "assets_ingested": ingest_stats["successful"],
                "assets_failed": ingest_stats["failed"],
                "duration_seconds": duration,
                "started_at": start_time.isoformat(),
                "completed_at": datetime.utcnow().isoformat(),
            }

            logger.info(f"Collection complete: {result}")
            return result

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Error during collection: {e}")

            return {
                "status": "failed",
                "assets_collected": 0,
                "assets_ingested": 0,
                "duration_seconds": duration,
                "error": str(e),
            }

    def list_available_snapshots(self) -> list[dict]:
        """
        List available AWS Config snapshots.

        Returns:
            list[dict]: List of available snapshots
        """
        try:
            return self.aws_config_collector.list_available_snapshots()
        except Exception as e:
            logger.error(f"Error listing snapshots: {e}")
            return []

    def get_collection_stats(self) -> dict:
        """
        Get current collection statistics.

        Returns:
            dict: Collection statistics
        """
        try:
            stats = self.graph_service.neo4j.get_stats()
            return {
                "total_assets": stats.get("total_assets", 0),
                "total_enrichments": stats.get("total_enrichments", 0),
                "total_relationships": stats.get("total_relationships", 0),
                "assets_by_type": stats.get("assets_by_type", []),
                "assets_by_region": stats.get("assets_by_region", []),
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
