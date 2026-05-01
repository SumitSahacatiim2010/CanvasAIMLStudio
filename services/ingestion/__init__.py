"""CanvasML Studio — Ingestion/ETL Engine.

DAG-based pipeline execution for data ingestion, transformation, and loading.
Supports full-load and incremental (high-watermark) modes.
"""

from services.connectors.base import ConnectorConfig


__all__ = ["PipelineConfig", "PipelineEngine"]
