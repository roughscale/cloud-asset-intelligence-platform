"""
Neo4j database client and schema management.
"""

import logging
from typing import Any, Optional
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError
from app.config import get_settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j database client with schema management."""

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """
        Initialize Neo4j client.

        Args:
            uri: Neo4j connection URI (bolt://...)
            user: Database username
            password: Database password
            database: Database name (default: neo4j)
        """
        self.uri = uri
        self.user = user
        self.database = database
        self._driver: Optional[Driver] = None

        try:
            self._driver = GraphDatabase.driver(
                uri, auth=(user, password), max_connection_lifetime=3600
            )
            logger.info(f"Successfully connected to Neo4j at {uri}")
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        """Close the database connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")

    def verify_connectivity(self) -> bool:
        """
        Verify database connectivity.

        Returns:
            bool: True if connected successfully
        """
        try:
            self._driver.verify_connectivity()
            return True
        except ServiceUnavailable:
            return False

    def session(self) -> Session:
        """
        Get a database session.

        Returns:
            Session: Neo4j session
        """
        return self._driver.session(database=self.database)

    def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> list:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            list: Query results
        """
        parameters = parameters or {}
        with self.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

    def execute_write(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """
        Execute a write transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Any: Transaction result
        """
        parameters = parameters or {}

        def _write_tx(tx):
            result = tx.run(query, parameters)
            return [record.data() for record in result]

        with self.session() as session:
            return session.execute_write(_write_tx)

    def initialize_schema(self):
        """
        Initialize database schema with constraints and indexes.
        This is idempotent - safe to run multiple times.
        """
        logger.info("Initializing Neo4j schema...")

        schema_queries = [
            # Constraints (ensure uniqueness)
            "CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT enrichment_id IF NOT EXISTS FOR (e:Enrichment) REQUIRE e.enrichment_id IS UNIQUE",

            # Indexes for common queries
            "CREATE INDEX asset_type IF NOT EXISTS FOR (a:Asset) ON (a.type)",
            "CREATE INDEX asset_account IF NOT EXISTS FOR (a:Asset) ON (a.account_id)",
            "CREATE INDEX asset_region IF NOT EXISTS FOR (a:Asset) ON (a.region)",
            "CREATE INDEX asset_name IF NOT EXISTS FOR (a:Asset) ON (a.name)",
            "CREATE INDEX enrichment_asset_id IF NOT EXISTS FOR (e:Enrichment) ON (e.asset_id)",
            "CREATE INDEX enrichment_status IF NOT EXISTS FOR (e:Enrichment) ON (e.status)",

            # Full-text search indexes (for asset names and tags)
            """
            CALL db.index.fulltext.createNodeIndex(
                'assetSearch',
                ['Asset'],
                ['name', 'description'],
                {eventually_consistent: 'true'}
            )
            """,
        ]

        with self.session() as session:
            for query in schema_queries:
                try:
                    # Skip if already exists (for full-text index)
                    if "assetSearch" in query:
                        # Check if index exists first
                        check_result = session.run(
                            "SHOW INDEXES YIELD name WHERE name = 'assetSearch' RETURN count(*) as count"
                        )
                        if check_result.single()["count"] > 0:
                            logger.info("Full-text index 'assetSearch' already exists")
                            continue

                    session.run(query)
                    logger.info(f"Schema query executed successfully")
                except Exception as e:
                    # Some constraint/index errors are expected if already exists
                    if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                        logger.debug(f"Schema element already exists: {e}")
                    else:
                        logger.warning(f"Schema query failed: {e}")

        logger.info("Schema initialization complete")

    def clear_database(self):
        """
        Clear all data from the database.
        WARNING: This deletes everything!
        """
        logger.warning("Clearing all data from Neo4j database...")
        query = "MATCH (n) DETACH DELETE n"
        self.execute_write(query)
        logger.info("Database cleared")

    def get_stats(self) -> dict[str, Any]:
        """
        Get database statistics.

        Returns:
            dict: Database statistics
        """
        queries = {
            "total_assets": "MATCH (a:Asset) RETURN count(a) as count",
            "total_enrichments": "MATCH (e:Enrichment) RETURN count(e) as count",
            "total_relationships": "MATCH ()-[r]->() RETURN count(r) as count",
            "assets_by_type": """
                MATCH (a:Asset)
                RETURN a.type as type, count(a) as count
                ORDER BY count DESC
            """,
            "assets_by_region": """
                MATCH (a:Asset)
                RETURN a.region as region, count(a) as count
                ORDER BY count DESC
            """,
        }

        stats = {}
        for key, query in queries.items():
            try:
                result = self.execute_query(query)
                if key in ["assets_by_type", "assets_by_region"]:
                    stats[key] = result
                else:
                    stats[key] = result[0]["count"] if result else 0
            except Exception as e:
                logger.error(f"Failed to get stat {key}: {e}")
                stats[key] = None

        return stats


# Global client instance
_neo4j_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """
    Get or create Neo4j client singleton.

    Returns:
        Neo4jClient: Database client instance
    """
    global _neo4j_client

    if _neo4j_client is None:
        settings = get_settings()
        _neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        # Initialize schema on first connection
        _neo4j_client.initialize_schema()

    return _neo4j_client


def close_neo4j_client():
    """Close the global Neo4j client."""
    global _neo4j_client
    if _neo4j_client:
        _neo4j_client.close()
        _neo4j_client = None
