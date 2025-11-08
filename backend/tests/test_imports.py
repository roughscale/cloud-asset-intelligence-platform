"""
Test that all modules can be imported without errors.
This catches missing __init__.py files and circular imports.
"""

import pytest


def test_import_config():
    """Test config module imports."""
    from app import config
    from app.config import Settings, get_settings
    assert config is not None
    assert Settings is not None
    assert get_settings is not None


def test_import_models():
    """Test model imports."""
    from app import models
    from app.models import Asset, Enrichment, AssetType
    from app.models.asset import AssetMetadata
    from app.models.enrichment import EnrichmentMetadata
    from app.models.enums import RelationshipType

    assert models is not None
    assert Asset is not None
    assert Enrichment is not None
    assert AssetType is not None


def test_import_db_clients():
    """Test database client imports."""
    from app import db
    from app.db import Neo4jClient, get_neo4j_client, close_neo4j_client
    from app.db import get_redis_client, close_redis_client

    assert db is not None
    assert Neo4jClient is not None
    assert get_neo4j_client is not None
    assert close_neo4j_client is not None
    assert get_redis_client is not None
    assert close_redis_client is not None


def test_import_collectors():
    """Test collector imports."""
    from app import collectors
    from app.collectors import AWSConfigCollector
    from app.collectors.base import BaseCollector

    assert collectors is not None
    assert AWSConfigCollector is not None
    assert BaseCollector is not None


def test_import_services():
    """Test service imports."""
    from app import services
    from app.services import GraphService, CollectionService

    assert services is not None
    assert GraphService is not None
    assert CollectionService is not None


def test_import_graphql():
    """Test GraphQL imports."""
    from app.api import graphql
    from app.api.graphql import schema
    from app.api.graphql import types
    from app.api.graphql.resolvers import asset_resolvers

    assert graphql is not None
    assert schema is not None
    assert types is not None
    assert asset_resolvers is not None


def test_import_main_app():
    """Test main application imports."""
    from app import main
    from app.main import app

    assert main is not None
    assert app is not None


def test_app_version():
    """Test app version is defined."""
    from app import __version__
    assert __version__ == "0.1.0"
