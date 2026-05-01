"""Observability REST API — monitoring, drift detection, and alerting endpoints.

Mounted at /api/v1/observability/* on the gateway.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from services.gateway.app.auth import CurrentUser, Role, get_current_user, require_roles
from services.observability.drift import DriftDetector, PerformanceMonitor

router = APIRouter(prefix="/api/v1/observability", tags=["Observability & Monitoring"])

_drift_detector = DriftDetector()
_perf_monitor = PerformanceMonitor()


class DriftCheckRequest(BaseModel):
    model_name: str = Field(...)
    baseline_data: list[dict[str, Any]] = Field(..., min_length=10)
    current_data: list[dict[str, Any]] = Field(..., min_length=10)
    features: list[str] | None = None


class PerformanceRecordRequest(BaseModel):
    model_name: str = Field(...)
    metrics: dict[str, float] = Field(...)
    prediction_count: int = Field(default=0, ge=0)
    avg_latency_ms: float = Field(default=0.0, ge=0)


@router.post("/drift/check")
async def check_drift(
    req: DriftCheckRequest,
    user: CurrentUser = Depends(require_roles(Role.DATA_SCIENTIST, Role.RISK_OFFICER, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Run drift detection between baseline and current data."""
    report = _drift_detector.detect_data_drift(
        baseline=req.baseline_data, current=req.current_data,
        model_name=req.model_name, features=req.features,
    )
    return {
        "report_id": report.report_id,
        "model_name": report.model_name,
        "overall_severity": report.overall_severity.value,
        "drift_percentage": report.drift_percentage,
        "drifted_features": report.drifted_features,
        "recommendations": report.recommendations,
        "feature_results": [
            {"feature": r.feature_name, "test": r.test_method,
             "statistic": r.statistic, "p_value": r.p_value,
             "severity": r.severity.value, "is_drifted": r.is_drifted}
            for r in report.feature_results
        ],
        "generated_at": report.generated_at.isoformat(),
    }


@router.post("/performance/record")
async def record_performance(
    req: PerformanceRecordRequest,
    user: CurrentUser = Depends(require_roles(Role.DATA_SCIENTIST, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Record model performance metrics."""
    snap = _perf_monitor.record(
        model_name=req.model_name, metrics=req.metrics,
        prediction_count=req.prediction_count, avg_latency_ms=req.avg_latency_ms,
    )
    return {
        "model_name": snap.model_name,
        "timestamp": snap.timestamp.isoformat(),
        "metrics": snap.metrics,
        "alerts": _perf_monitor.get_alerts(req.model_name),
    }


@router.get("/performance/{model_name}")
async def get_performance_history(
    model_name: str,
    last_n: int = Query(default=50, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get performance history for a model."""
    history = _perf_monitor.get_history(model_name, last_n)
    return {
        "model_name": model_name,
        "snapshots": [
            {"timestamp": s.timestamp.isoformat(), "metrics": s.metrics,
             "predictions": s.prediction_count, "latency_ms": s.avg_latency_ms}
            for s in history
        ],
        "total": len(history),
    }


@router.get("/alerts")
async def get_alerts(
    model_name: str | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get monitoring alerts."""
    alerts = _perf_monitor.get_alerts(model_name)
    return {"alerts": alerts, "total": len(alerts)}
