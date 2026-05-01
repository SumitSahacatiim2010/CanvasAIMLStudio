"""CSV connector — connects to local or mounted CSV/TSV files.

Lightweight connector for file-based data sources. Supports
directory scanning, column type inference, and streaming extraction.
"""

import csv
import os
from pathlib import Path
from typing import Any

from services.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorStatus,
    ExtractionResult,
    FieldInfo,
    SchemaInfo,
)


def _infer_type(value: str) -> str:
    """Infer column type from a string value."""
    if not value or value.strip() == "":
        return "string"
    try:
        int(value)
        return "int"
    except ValueError:
        pass
    try:
        float(value)
        return "float"
    except ValueError:
        pass
    if value.lower() in ("true", "false"):
        return "boolean"
    return "string"


class CSVConnector(BaseConnector):
    """Connector for local CSV/TSV files or directories."""

    def validate_config(self) -> tuple[bool, list[str]]:
        errors = []
        if "path" not in self.config.config:
            errors.append("Missing required config key: path")
        else:
            path = Path(self.config.config["path"])
            if not path.exists():
                errors.append(f"Path does not exist: {path}")
        return (len(errors) == 0, errors)

    def connect(self) -> None:
        self.status = ConnectorStatus.ACTIVE

    def disconnect(self) -> None:
        self.status = ConnectorStatus.INACTIVE

    def test_connectivity(self) -> tuple[bool, str]:
        path = Path(self.config.config["path"])
        if path.exists():
            return (True, f"Path accessible: {path}")
        return (False, f"Path not found: {path}")

    def discover_schemas(self) -> list[SchemaInfo]:
        path = Path(self.config.config["path"])
        schemas: list[SchemaInfo] = []
        delimiter = self.config.config.get("delimiter", ",")

        files = [path] if path.is_file() else sorted(path.glob("**/*.csv")) + sorted(path.glob("**/*.tsv"))

        for file_path in files:
            if file_path.suffix.lower() == ".tsv":
                delimiter = "\t"

            fields: list[FieldInfo] = []
            row_count = 0

            with open(file_path, "r", encoding=self.config.config.get("encoding", "utf-8")) as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                sample_rows: list[dict[str, str]] = []
                for i, row in enumerate(reader):
                    row_count += 1
                    if i < 100:  # Sample first 100 rows for type inference
                        sample_rows.append(row)

                if sample_rows and reader.fieldnames:
                    for col_name in reader.fieldnames:
                        sample_values = [r.get(col_name, "") for r in sample_rows if r.get(col_name)]
                        inferred = _infer_type(sample_values[0]) if sample_values else "string"
                        fields.append(FieldInfo(name=col_name, dtype=inferred))

            schemas.append(
                SchemaInfo(
                    name=str(file_path),
                    fields=fields,
                    row_count=row_count,
                    size_bytes=file_path.stat().st_size,
                )
            )

        return schemas

    def extract(
        self,
        schema_name: str,
        columns: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        high_watermark: Any | None = None,
    ) -> ExtractionResult:
        file_path = Path(schema_name)
        delimiter = self.config.config.get("delimiter", ",")
        if file_path.suffix.lower() == ".tsv":
            delimiter = "\t"

        rows: list[dict[str, Any]] = []

        with open(file_path, "r", encoding=self.config.config.get("encoding", "utf-8")) as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break

                # Apply filters
                if filters:
                    skip = False
                    for col, val in filters.items():
                        if str(row.get(col, "")) != str(val):
                            skip = True
                            break
                    if skip:
                        continue

                # Apply column projection
                if columns:
                    row = {k: v for k, v in row.items() if k in columns}

                rows.append(dict(row))

        col_names = list(rows[0].keys()) if rows else []

        return ExtractionResult(
            schema_name=schema_name,
            columns=col_names,
            rows=rows,
            row_count=len(rows),
        )
