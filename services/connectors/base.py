"""Base connector interface — all data source connectors implement this contract.

Design follows the Blueprint §2.1: each connector provides lifecycle methods
for configuration validation, connectivity testing, schema discovery, and data extraction.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generator, Iterator


class ConnectorStatus(str, Enum):
    """Connector health status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"


@dataclass
class FieldInfo:
    """Metadata for a single column/field in a dataset."""

    name: str
    dtype: str
    nullable: bool = True
    description: str = ""
    pii_classification: str = "none"  # none, quasi, direct, sensitive


@dataclass
class SchemaInfo:
    """Discovered schema for a table/file/object."""

    name: str
    fields: list[FieldInfo]
    row_count: int | None = None
    size_bytes: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorConfig:
    """Base connector configuration."""

    name: str
    connector_type: str
    config: dict[str, Any]  # Connection-specific params (encrypted at rest)
    description: str = ""


@dataclass
class ExtractionResult:
    """Result of a data extraction operation."""

    schema_name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    high_watermark: Any | None = None  # For incremental extraction
    extracted_at: datetime = field(default_factory=datetime.utcnow)


class BaseConnector(ABC):
    """Abstract base class for all data source connectors.

    Lifecycle:
        1. validate_config() — check configuration completeness
        2. test_connectivity() — verify the source is reachable
        3. discover_schemas() — list available tables/files/objects
        4. extract() — pull data from a specific schema

    Subclasses must implement all abstract methods.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self.status = ConnectorStatus.INACTIVE
        self._connection: Any = None

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def connector_type(self) -> str:
        return self.config.connector_type

    # ── Lifecycle Methods ────────────────────────────────

    @abstractmethod
    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate the connector configuration.

        Returns:
            (is_valid, list_of_errors)
        """
        ...

    @abstractmethod
    def test_connectivity(self) -> tuple[bool, str]:
        """Test connectivity to the data source.

        Returns:
            (is_connected, message)
        """
        ...

    @abstractmethod
    def discover_schemas(self) -> list[SchemaInfo]:
        """Discover available schemas/tables/files in the source.

        Returns:
            List of SchemaInfo objects describing each available dataset.
        """
        ...

    @abstractmethod
    def extract(
        self,
        schema_name: str,
        columns: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        high_watermark: Any | None = None,
    ) -> ExtractionResult:
        """Extract data from a specific schema.

        Args:
            schema_name: Table/file/object to extract from.
            columns: Optional column subset (projection pushdown).
            filters: Optional filter conditions (predicate pushdown).
            limit: Maximum rows to extract.
            high_watermark: For incremental extraction — only rows after this value.

        Returns:
            ExtractionResult with data and metadata.
        """
        ...

    def extract_stream(
        self,
        schema_name: str,
        columns: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        batch_size: int = 1000,
        high_watermark: Any | None = None,
    ) -> Iterator[ExtractionResult]:
        """Stream data in batches. Default implementation calls extract() with limit.

        Override for connectors that support native cursor-based streaming.
        """
        offset = 0
        while True:
            result = self.extract(
                schema_name=schema_name,
                columns=columns,
                filters=filters,
                limit=batch_size,
                high_watermark=high_watermark,
            )
            if not result.rows:
                break
            yield result
            offset += len(result.rows)
            if len(result.rows) < batch_size:
                break

    # ── Connection Management ────────────────────────────

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the data source."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the data source."""
        ...

    def __enter__(self) -> "BaseConnector":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name!r}, status={self.status.value})>"
