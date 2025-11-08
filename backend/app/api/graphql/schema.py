"""
GraphQL schema definition.
"""

import strawberry
from typing import Optional
from app.api.graphql.types import Asset, AssetFilter, Query

# Create GraphQL schema
schema = strawberry.Schema(query=Query)
