"""CanvasML Studio — Connector Framework.

Provides a pluggable architecture for connecting to heterogeneous data sources.
Each connector implements the BaseConnector interface for schema discovery and extraction.
"""

from services.connectors.base import BaseConnector, ConnectorConfig, ConnectorStatus, SchemaInfo

__all__ = ["BaseConnector", "ConnectorConfig", "ConnectorStatus", "SchemaInfo"]
