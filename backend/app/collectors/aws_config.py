"""
AWS Config collector for ingesting configuration snapshots from S3.
"""

import json
import logging
from datetime import datetime
from typing import Any
from app.collectors.base import BaseCollector
from app.models.enums import AWS_CONFIG_TYPE_MAPPING, AssetType
from app.models.asset import Asset, AssetMetadata

logger = logging.getLogger(__name__)


class AWSConfigCollector(BaseCollector):
    """Collector for AWS Config snapshots stored in S3."""

    def __init__(self):
        """Initialize AWS Config collector."""
        super().__init__()
        self.s3_client = self.get_client("s3")
        self.config_bucket = self.settings.aws_config_bucket

    def collect(self, s3_key: str | None = None) -> list[Asset]:
        """
        Collect assets from AWS Config snapshot.

        Args:
            s3_key: Specific S3 key to process. If None, processes latest snapshot.

        Returns:
            list[Asset]: List of collected assets
        """
        logger.info(
            f"Starting AWS Config collection from bucket: {self.config_bucket}"
        )

        try:
            # If no specific key provided, get the latest snapshot
            if not s3_key:
                s3_key = self._get_latest_snapshot_key()

            if not s3_key:
                logger.warning("No AWS Config snapshot found")
                return []

            # Download and parse the snapshot
            snapshot_data = self._download_snapshot(s3_key)

            if not snapshot_data:
                logger.warning(f"Failed to download snapshot: {s3_key}")
                return []

            # Transform configuration items to assets
            assets = []
            config_items = snapshot_data.get("configurationItems", [])
            logger.info(f"Processing {len(config_items)} configuration items")

            for config_item in config_items:
                try:
                    asset = self.transform(config_item)
                    if asset:
                        assets.append(asset)
                except Exception as e:
                    logger.error(
                        f"Failed to transform config item {config_item.get('resourceId')}: {e}"
                    )
                    continue

            logger.info(f"Successfully collected {len(assets)} assets")
            return assets

        except Exception as e:
            logger.error(f"Error collecting from AWS Config: {e}")
            return []

    def _get_latest_snapshot_key(self) -> str | None:
        """
        Get the latest Config snapshot key from S3.

        Returns:
            str | None: S3 key of latest snapshot or None
        """
        try:
            # AWS Config typically stores snapshots in a date-based structure
            # Format: AWSLogs/{account-id}/Config/{region}/YYYY/MM/DD/ConfigSnapshot/...

            # For simplicity in Phase 1, list all objects and get the most recent
            # In production, you'd want to optimize this with prefixes

            response = self.s3_client.list_objects_v2(
                Bucket=self.config_bucket,
                Prefix="AWSLogs/",
                MaxKeys=1000
            )

            if "Contents" not in response:
                return None

            # Filter for ConfigSnapshot files and get the most recent
            snapshot_files = [
                obj
                for obj in response["Contents"]
                if "ConfigSnapshot" in obj["Key"]
                and obj["Key"].endswith(".json.gz")
            ]

            if not snapshot_files:
                return None

            # Sort by last modified and get the latest
            latest = max(snapshot_files, key=lambda x: x["LastModified"])
            logger.info(f"Found latest snapshot: {latest['Key']}")
            return latest["Key"]

        except Exception as e:
            logger.error(f"Error finding latest snapshot: {e}")
            return None

    def _download_snapshot(self, s3_key: str) -> dict | None:
        """
        Download and parse Config snapshot from S3.

        Args:
            s3_key: S3 key of the snapshot

        Returns:
            dict | None: Parsed snapshot data or None
        """
        try:
            logger.info(f"Downloading snapshot: {s3_key}")

            response = self.s3_client.get_object(Bucket=self.config_bucket, Key=s3_key)
            content = response["Body"].read()

            # Handle gzip compression if needed
            if s3_key.endswith(".gz"):
                import gzip
                content = gzip.decompress(content)

            # Parse JSON
            snapshot_data = json.loads(content)
            logger.info(f"Successfully downloaded and parsed snapshot")
            return snapshot_data

        except Exception as e:
            logger.error(f"Error downloading snapshot {s3_key}: {e}")
            return None

    def transform(self, config_item: dict[str, Any]) -> Asset | None:
        """
        Transform AWS Config item to Asset model.

        Args:
            config_item: AWS Config configuration item

        Returns:
            Asset | None: Transformed asset or None if unsupported type
        """
        try:
            resource_type = config_item.get("resourceType")

            # Map AWS Config resource type to our AssetType
            asset_type = AWS_CONFIG_TYPE_MAPPING.get(resource_type, AssetType.UNKNOWN)

            # Skip unknown types
            if asset_type == AssetType.UNKNOWN:
                logger.debug(f"Skipping unknown resource type: {resource_type}")
                return None

            # Extract core fields
            resource_id = config_item.get("resourceId")
            resource_name = config_item.get("resourceName", resource_id)
            arn = config_item.get("ARN", resource_id)
            region = config_item.get("awsRegion", self.settings.aws_region)
            account_id = config_item.get("awsAccountId", "")

            # Extract tags
            tags = {}
            if "tags" in config_item:
                tags = config_item["tags"]
            elif "supplementaryConfiguration" in config_item:
                # Some resources store tags in supplementaryConfiguration
                supp_config = config_item["supplementaryConfiguration"]
                if "Tags" in supp_config:
                    tags = supp_config["Tags"]

            # Get configuration
            configuration = config_item.get("configuration", {})

            # Get state/status
            config_status = config_item.get("configurationItemStatus")
            resource_status = config_item.get("resourceStatus")
            state = resource_status or config_status

            # Create metadata
            capture_time = config_item.get("configurationItemCaptureTime")
            creation_time = config_item.get("resourceCreationTime")

            metadata = AssetMetadata(
                source="aws_config",
                discovered_at=datetime.fromisoformat(capture_time.replace("Z", "+00:00"))
                if capture_time
                else datetime.utcnow(),
                last_seen=datetime.utcnow(),
                last_modified=datetime.fromisoformat(creation_time.replace("Z", "+00:00"))
                if creation_time
                else None,
                config_snapshot_time=datetime.fromisoformat(
                    capture_time.replace("Z", "+00:00")
                )
                if capture_time
                else None,
            )

            # Create Asset
            asset = Asset(
                id=arn,
                type=asset_type,
                name=resource_name,
                region=region,
                account_id=account_id,
                availability_zone=config_item.get("availabilityZone"),
                source_tags=tags,
                configuration=configuration,
                metadata=metadata,
                state=state,
            )

            return asset

        except Exception as e:
            logger.error(f"Error transforming config item: {e}")
            return None

    def list_available_snapshots(self) -> list[dict]:
        """
        List all available Config snapshots in S3.

        Returns:
            list[dict]: List of snapshot metadata
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config_bucket, Prefix="AWSLogs/"
            )

            if "Contents" not in response:
                return []

            snapshots = [
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"],
                }
                for obj in response["Contents"]
                if "ConfigSnapshot" in obj["Key"] and obj["Key"].endswith(".json.gz")
            ]

            # Sort by last modified (newest first)
            snapshots.sort(key=lambda x: x["last_modified"], reverse=True)

            return snapshots

        except Exception as e:
            logger.error(f"Error listing snapshots: {e}")
            return []
