"""Pipeline configuration and execution engine.

Pipelines are defined as YAML/JSON configs specifying source, transforms,
and destination. The engine loads configs, validates them, and executes
the DAG of extraction → transformation → load steps.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from services.connectors.base import ConnectorConfig, ExtractionResult
from services.connectors.factory import create_connector


class PipelineStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class LoadMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


@dataclass
class TransformStep:
    """A single transformation step in the pipeline."""

    name: str
    type: str  # rename_columns, cast_types, filter_rows, add_column, drop_columns
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Configuration for an ingestion pipeline."""

    name: str
    source: ConnectorConfig
    target_dataset: str
    load_mode: LoadMode = LoadMode.FULL
    high_watermark_column: str | None = None
    transforms: list[TransformStep] = field(default_factory=list)
    schedule: str | None = None  # Cron expression for scheduling
    retry_count: int = 3
    retry_delay_seconds: int = 60


@dataclass
class PipelineRun:
    """Record of a single pipeline execution."""

    pipeline_name: str
    status: PipelineStatus = PipelineStatus.CREATED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    rows_extracted: int = 0
    rows_loaded: int = 0
    error_message: str | None = None
    high_watermark: Any = None


class PipelineEngine:
    """Executes ingestion pipelines.

    Workflow:
        1. Load pipeline config
        2. Create connector from source config
        3. Extract data (full or incremental)
        4. Apply transform steps
        5. Load to target (currently returns data; Phase 1.5 will add actual load targets)
    """

    def __init__(self) -> None:
        self._runs: list[PipelineRun] = []

    def execute(self, config: PipelineConfig) -> PipelineRun:
        """Execute a pipeline and return the run record."""
        run = PipelineRun(pipeline_name=config.name, started_at=datetime.utcnow())
        run.status = PipelineStatus.RUNNING

        try:
            # 1. Create and connect to source
            connector = create_connector(config.source)
            valid, errors = connector.validate_config()
            if not valid:
                raise ValueError(f"Invalid connector config: {errors}")

            connector.connect()

            try:
                # 2. Discover available schemas
                schemas = connector.discover_schemas()
                if not schemas:
                    raise ValueError(f"No schemas found in source: {config.source.name}")

                # Find target schema (first match by name, or first available)
                target_schema = next(
                    (s for s in schemas if config.target_dataset in s.name),
                    schemas[0],
                )

                # 3. Extract data
                hwm = run.high_watermark if config.load_mode == LoadMode.INCREMENTAL else None
                result = connector.extract(
                    schema_name=target_schema.name,
                    high_watermark=hwm,
                )
                run.rows_extracted = result.row_count

                # 4. Apply transforms
                transformed_rows = self._apply_transforms(result.rows, config.transforms)

                # 5. Record results
                run.rows_loaded = len(transformed_rows)
                run.status = PipelineStatus.COMPLETED
                run.completed_at = datetime.utcnow()

                if config.high_watermark_column and transformed_rows:
                    last_row = transformed_rows[-1]
                    run.high_watermark = last_row.get(config.high_watermark_column)

            finally:
                connector.disconnect()

        except Exception as e:
            run.status = PipelineStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()

        self._runs.append(run)
        return run

    def _apply_transforms(
        self, rows: list[dict[str, Any]], transforms: list[TransformStep]
    ) -> list[dict[str, Any]]:
        """Apply a chain of transformation steps to the extracted data."""
        result = rows

        for step in transforms:
            if step.type == "rename_columns":
                mapping = step.config.get("mapping", {})
                result = [{mapping.get(k, k): v for k, v in row.items()} for row in result]

            elif step.type == "drop_columns":
                drop_cols = set(step.config.get("columns", []))
                result = [{k: v for k, v in row.items() if k not in drop_cols} for row in result]

            elif step.type == "filter_rows":
                col = step.config.get("column", "")
                op = step.config.get("operator", "eq")
                val = step.config.get("value")
                filtered = []
                for row in result:
                    cell = row.get(col)
                    if op == "eq" and cell == val:
                        filtered.append(row)
                    elif op == "neq" and cell != val:
                        filtered.append(row)
                    elif op == "gt" and cell is not None and cell > val:
                        filtered.append(row)
                    elif op == "lt" and cell is not None and cell < val:
                        filtered.append(row)
                result = filtered

            elif step.type == "cast_types":
                casts = step.config.get("columns", {})
                for row in result:
                    for col, target_type in casts.items():
                        if col in row and row[col] is not None:
                            try:
                                if target_type == "int":
                                    row[col] = int(row[col])
                                elif target_type == "float":
                                    row[col] = float(row[col])
                                elif target_type == "string":
                                    row[col] = str(row[col])
                                elif target_type == "boolean":
                                    row[col] = str(row[col]).lower() in ("true", "1", "yes")
                            except (ValueError, TypeError):
                                pass  # Keep original value on cast failure

            elif step.type == "add_column":
                col_name = step.config.get("name", "new_column")
                col_value = step.config.get("value")
                result = [{**row, col_name: col_value} for row in result]

        return result

    def get_runs(self, pipeline_name: str | None = None) -> list[PipelineRun]:
        """Get pipeline run history, optionally filtered by pipeline name."""
        if pipeline_name:
            return [r for r in self._runs if r.pipeline_name == pipeline_name]
        return list(self._runs)
