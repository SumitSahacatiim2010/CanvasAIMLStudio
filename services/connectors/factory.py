"""Connector factory — instantiates the correct connector by type."""

from services.connectors.base import BaseConnector, ConnectorConfig
from services.connectors.csv_connector import CSVConnector
from services.connectors.postgres_connector import PostgresConnector
from services.connectors.s3_connector import S3Connector

# Registry of available connector types
CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] = {
    "postgres": PostgresConnector,
    "postgresql": PostgresConnector,
    "s3": S3Connector,
    "minio": S3Connector,
    "csv": CSVConnector,
    "tsv": CSVConnector,
}


def create_connector(config: ConnectorConfig) -> BaseConnector:
    """Factory method — create a connector instance from config.

    Args:
        config: ConnectorConfig with connector_type and connection params.

    Returns:
        Instantiated connector ready for connect().

    Raises:
        ValueError: If connector_type is not in the registry.
    """
    connector_type = config.connector_type.lower()
    if connector_type not in CONNECTOR_REGISTRY:
        available = ", ".join(sorted(CONNECTOR_REGISTRY.keys()))
        raise ValueError(f"Unknown connector type: {connector_type!r}. Available: {available}")

    connector_class = CONNECTOR_REGISTRY[connector_type]
    return connector_class(config)


def list_connector_types() -> list[str]:
    """Return all registered connector type names."""
    return sorted(set(CONNECTOR_REGISTRY.keys()))
