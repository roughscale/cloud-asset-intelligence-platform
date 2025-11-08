"""
Main FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from app.config import get_settings
from app.db import get_neo4j_client, get_redis_client, close_neo4j_client, close_redis_client
from app.api.graphql.schema import schema
from app import __version__

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting Asset Inventory API v{__version__}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"AWS Region: {settings.aws_region}")

    # Initialize database connections
    try:
        neo4j_client = get_neo4j_client()
        if neo4j_client.verify_connectivity():
            logger.info("✓ Neo4j connection verified")
            stats = neo4j_client.get_stats()
            logger.info(f"✓ Database stats: {stats.get('total_assets', 0)} assets")
        else:
            logger.error("✗ Neo4j connection failed")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Neo4j: {e}")

    try:
        redis_client = get_redis_client()
        logger.info("✓ Redis connection verified")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Redis: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Asset Inventory API")
    close_neo4j_client()
    close_redis_client()


# Create FastAPI application
app = FastAPI(
    title="Asset Inventory API",
    description="Cloud Asset Intelligence Platform - CMDB and Asset Inventory with LLM integration",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    neo4j_client = get_neo4j_client()
    redis_client = get_redis_client()

    neo4j_healthy = neo4j_client.verify_connectivity()
    redis_healthy = redis_client.exists("__health_check__") >= 0

    return {
        "status": "healthy" if (neo4j_healthy and redis_healthy) else "degraded",
        "version": __version__,
        "services": {
            "neo4j": "healthy" if neo4j_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
        },
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Asset Inventory API",
        "version": __version__,
        "environment": settings.environment,
        "graphql_endpoint": "/graphql",
        "docs": "/docs",
    }


# Database stats endpoint
@app.get("/stats")
async def get_stats():
    """Get database statistics."""
    neo4j_client = get_neo4j_client()
    return neo4j_client.get_stats()


# Collection endpoints
@app.post("/api/collect/aws-config")
async def trigger_aws_config_collection(s3_key: str | None = None):
    """
    Trigger AWS Config collection.

    Args:
        s3_key: Optional specific S3 key to process. If None, processes latest snapshot.

    Returns:
        dict: Collection results
    """
    from app.services import CollectionService

    collection_service = CollectionService()
    return collection_service.collect_from_aws_config(s3_key)


@app.get("/api/collect/snapshots")
async def list_snapshots():
    """List available AWS Config snapshots."""
    from app.services import CollectionService

    collection_service = CollectionService()
    return collection_service.list_available_snapshots()


# GraphQL endpoint
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
    )
