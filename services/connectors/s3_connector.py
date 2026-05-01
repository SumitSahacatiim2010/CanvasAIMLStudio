"""S3 / MinIO connector — connects to S3-compatible object storage.

Discovers buckets and objects, extracts CSV/Parquet/JSON files.
Supports prefix-based filtering and streaming extraction.
"""

from io import BytesIO, StringIO
from typing import Any

from services.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorStatus,
    ExtractionResult,
    FieldInfo,
    SchemaInfo,
)


class S3Connector(BaseConnector):
    """Connector for S3 and MinIO object storage."""

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._client: Any = None

    def validate_config(self) -> tuple[bool, list[str]]:
        errors = []
        for key in ["endpoint", "access_key", "secret_key", "bucket"]:
            if key not in self.config.config:
                errors.append(f"Missing required config key: {key}")
        return (len(errors) == 0, errors)

    def connect(self) -> None:
        import boto3
        from botocore.client import Config

        cfg = self.config.config
        self._client = boto3.client(
            "s3",
            endpoint_url=cfg["endpoint"],
            aws_access_key_id=cfg["access_key"],
            aws_secret_access_key=cfg["secret_key"],
            config=Config(signature_version="s3v4"),
            region_name=cfg.get("region", "us-east-1"),
        )
        self.status = ConnectorStatus.ACTIVE

    def disconnect(self) -> None:
        self._client = None
        self.status = ConnectorStatus.INACTIVE

    def test_connectivity(self) -> tuple[bool, str]:
        try:
            self.connect()
            bucket = self.config.config["bucket"]
            self._client.head_bucket(Bucket=bucket)
            self.disconnect()
            return (True, f"Connected to bucket: {bucket}")
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            return (False, str(e))

    def discover_schemas(self) -> list[SchemaInfo]:
        bucket = self.config.config["bucket"]
        prefix = self.config.config.get("prefix", "")
        schemas: list[SchemaInfo] = []

        paginator = self._client.get_paginator("list_objects_v2")
        supported_ext = (".csv", ".json", ".jsonl", ".parquet", ".tsv")

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if any(key.lower().endswith(ext) for ext in supported_ext):
                    schemas.append(
                        SchemaInfo(
                            name=key,
                            fields=[],  # Populated on first extract
                            size_bytes=obj.get("Size"),
                            metadata={"bucket": bucket, "last_modified": str(obj.get("LastModified", ""))},
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
        import csv
        import json

        bucket = self.config.config["bucket"]
        response = self._client.get_object(Bucket=bucket, Key=schema_name)
        body = response["Body"].read()

        rows: list[dict[str, Any]] = []

        if schema_name.lower().endswith(".csv") or schema_name.lower().endswith(".tsv"):
            delimiter = "\t" if schema_name.lower().endswith(".tsv") else ","
            text = body.decode("utf-8")
            reader = csv.DictReader(StringIO(text), delimiter=delimiter)
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                rows.append(dict(row))

        elif schema_name.lower().endswith(".json"):
            data = json.loads(body)
            if isinstance(data, list):
                rows = data[:limit] if limit else data
            else:
                rows = [data]

        elif schema_name.lower().endswith(".jsonl"):
            for i, line in enumerate(body.decode("utf-8").strip().split("\n")):
                if limit and i >= limit:
                    break
                rows.append(json.loads(line))

        elif schema_name.lower().endswith(".parquet"):
            import pyarrow.parquet as pq

            table = pq.read_table(BytesIO(body))
            df = table.to_pandas()
            if limit:
                df = df.head(limit)
            rows = df.to_dict("records")

        # Apply column projection
        if columns and rows:
            rows = [{k: v for k, v in row.items() if k in columns} for row in rows]

        col_names = list(rows[0].keys()) if rows else []

        return ExtractionResult(
            schema_name=schema_name,
            columns=col_names,
            rows=rows,
            row_count=len(rows),
        )
