"""PostgreSQL connector — connects to Postgres/pgvector databases.

Supports schema discovery via information_schema, predicate pushdown,
projection pushdown, and incremental extraction via high-watermark columns.
"""

from typing import Any

import psycopg2
import psycopg2.extras

from services.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorStatus,
    ExtractionResult,
    FieldInfo,
    SchemaInfo,
)

# Map Postgres types to simplified type names
PG_TYPE_MAP: dict[str, str] = {
    "integer": "int",
    "bigint": "bigint",
    "smallint": "smallint",
    "numeric": "decimal",
    "real": "float",
    "double precision": "double",
    "character varying": "string",
    "character": "string",
    "text": "string",
    "boolean": "boolean",
    "date": "date",
    "timestamp without time zone": "timestamp",
    "timestamp with time zone": "timestamp_tz",
    "uuid": "uuid",
    "jsonb": "json",
    "json": "json",
    "bytea": "binary",
}


class PostgresConnector(BaseConnector):
    """Connector for PostgreSQL and pgvector databases."""

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._required_keys = ["host", "port", "database", "user", "password"]

    def validate_config(self) -> tuple[bool, list[str]]:
        errors = []
        for key in self._required_keys:
            if key not in self.config.config:
                errors.append(f"Missing required config key: {key}")
        if "port" in self.config.config:
            try:
                int(self.config.config["port"])
            except (ValueError, TypeError):
                errors.append("Port must be a valid integer")
        return (len(errors) == 0, errors)

    def connect(self) -> None:
        cfg = self.config.config
        self._connection = psycopg2.connect(
            host=cfg["host"],
            port=int(cfg["port"]),
            database=cfg["database"],
            user=cfg["user"],
            password=cfg["password"],
            options=cfg.get("options", ""),
        )
        self.status = ConnectorStatus.ACTIVE

    def disconnect(self) -> None:
        if self._connection and not self._connection.closed:
            self._connection.close()
        self.status = ConnectorStatus.INACTIVE

    def test_connectivity(self) -> tuple[bool, str]:
        try:
            self.connect()
            with self._connection.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
            self.disconnect()
            return (True, f"Connected: {version}")
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            return (False, str(e))

    def discover_schemas(self) -> list[SchemaInfo]:
        schema = self.config.config.get("schema", "public")
        schemas: list[SchemaInfo] = []

        with self._connection.cursor() as cur:
            # Get all tables
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """,
                (schema,),
            )
            tables = [row[0] for row in cur.fetchall()]

            for table in tables:
                # Get columns
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (schema, table),
                )
                fields = [
                    FieldInfo(
                        name=row[0],
                        dtype=PG_TYPE_MAP.get(row[1], row[1]),
                        nullable=row[2] == "YES",
                    )
                    for row in cur.fetchall()
                ]

                # Get row count estimate
                cur.execute(
                    f"SELECT reltuples::bigint FROM pg_class WHERE relname = %s",  # noqa: S608
                    (table,),
                )
                count_row = cur.fetchone()
                row_count = int(count_row[0]) if count_row and count_row[0] >= 0 else None

                schemas.append(SchemaInfo(name=table, fields=fields, row_count=row_count))

        return schemas

    def extract(
        self,
        schema_name: str,
        columns: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        high_watermark: Any | None = None,
    ) -> ExtractionResult:
        col_clause = ", ".join(columns) if columns else "*"
        query = f"SELECT {col_clause} FROM {schema_name}"  # noqa: S608
        params: list[Any] = []

        # Predicate pushdown
        where_clauses: list[str] = []
        if filters:
            for col, val in filters.items():
                where_clauses.append(f"{col} = %s")
                params.append(val)
        if high_watermark:
            hwm_col = self.config.config.get("high_watermark_column", "updated_at")
            where_clauses.append(f"{hwm_col} > %s")
            params.append(high_watermark)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        if limit:
            query += f" LIMIT {limit}"

        with self._connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            rows = [dict(row) for row in cur.fetchall()]
            col_names = [desc[0] for desc in cur.description] if cur.description else []

        return ExtractionResult(
            schema_name=schema_name,
            columns=col_names,
            rows=rows,
            row_count=len(rows),
        )
