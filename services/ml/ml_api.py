"""ML Pipeline REST API — model registry, experiments, and training endpoints.

Mounted at /api/v1/ml/* on the gateway.
Wraps services/ml/registry.py and services/ml/training.py.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from services.gateway.app.auth import CurrentUser, Role, get_current_user, require_roles
from services.ml.registry import ModelRegistry, ModelStatus, RegisteredModel
from services.ml.training import TrainingConfig, TrainingService
from services.ml.experimentation import ExperimentationService
from services.ml.monitoring import MonitoringService
from services.ml.db import SessionLocal
from services.agentic.automl_workflow import run_auto_mode

router = APIRouter(prefix="/api/v1/ml", tags=["ML Pipeline"])

# Singletons — PostgreSQL-backed as of Phase 4
_registry = ModelRegistry(registry_path="./model_registry")
_trainer = TrainingService()
_monitor = MonitoringService()
_experiment_service = ExperimentationService(_registry, _trainer, _monitor)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class RegisterModelRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    algorithm: str = Field(..., description="e.g. XGBoost, Random Forest, LightGBM")
    metrics: dict[str, float] = Field(..., description="e.g. {f1: 0.89, auc: 0.94}")
    feature_names: list[str] = Field(default_factory=list)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, str] = Field(default_factory=dict)
    drift_status: Literal["none", "low", "moderate", "high"] = "none"


class UpdateStatusRequest(BaseModel):
    status: Literal["trained", "validated", "deployed", "retired", "failed"]


class ExperimentRequest(BaseModel):
    experiment_name: str = Field(..., min_length=1, max_length=64)
    task_type: Literal["binary_classification", "multiclass_classification", "regression"] = "binary_classification"
    algorithms: list[str] = Field(
        default=["logistic_regression", "random_forest", "gradient_boosting"],
        description="Algorithms to train and compare",
    )
    target_column: str = Field(default="target")
    test_size: float = Field(default=0.2, ge=0.1, le=0.5)
    cv_folds: int = Field(default=5, ge=2, le=10)
    # Training data — small synthetic dataset is generated if omitted
    data: list[dict[str, Any]] | None = Field(
        default=None,
        description="Training data as list of row dicts. Omit to use a synthetic demo dataset.",
    )


class PredictionLogRequest(BaseModel):
    model_id: str
    features: dict[str, Any]
    prediction: float
    metadata: dict[str, Any] | None = None


class ActualValueRequest(BaseModel):
    actual_value: float


class AutoMLRequest(BaseModel):
    dataset_id: str | None = Field(default=None)
    dataset_path: str = Field(...)
    target_column: str | None = Field(default=None)


def _model_to_dict(m: RegisteredModel) -> dict[str, Any]:
    return {
        "model_id": m.model_id,
        "name": m.name,
        "version": m.version,
        "algorithm": m.algorithm,
        "status": m.status.value,
        "metrics": m.metrics,
        "feature_names": m.feature_names,
        "hyperparameters": m.hyperparameters,
        "tags": m.tags,
        "created_by": m.created_by,
        "created_at": m.created_at.isoformat(),
        "updated_at": m.updated_at.isoformat(),
        # Drift is stored as a tag for flexibility
        "drift": m.tags.get("drift", "none"),
        "trained_at": m.tags.get("trained_at", m.created_at.strftime("%Y-%m-%d")),
    }


# ── Model Registry Endpoints ─────────────────────────────────────────────────

@router.get("/models")
async def list_models(
    status_filter: str | None = Query(default=None, alias="status"),
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all registered models, optionally filtered by status."""
    status_enum = ModelStatus(status_filter) if status_filter else None
    models = _registry.list_models(status=status_enum)
    return {
        "models": [_model_to_dict(m) for m in models],
        "total": len(models),
    }


@router.post("/models", status_code=status.HTTP_201_CREATED)
async def register_model(
    req: RegisterModelRequest,
    user: CurrentUser = Depends(require_roles(Role.DATA_SCIENTIST, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Register a pre-trained model in the registry."""
    # Use a placeholder object when registering externally-trained models
    tags = req.tags.copy()
    tags["drift"] = req.drift_status
    tags["trained_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tags["registered_via"] = "api"

    registered = _registry.register(
        name=req.name,
        model_object={"external": True, "algorithm": req.algorithm},
        algorithm=req.algorithm,
        metrics=req.metrics,
        feature_names=req.feature_names,
        hyperparameters=req.hyperparameters,
        tags=tags,
        created_by=user.email,
    )
    return _model_to_dict(registered)


@router.get("/models/{model_name}")
async def get_model(
    model_name: str,
    version: int | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific model (latest version by default)."""
    model = _registry.get_model(model_name, version)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    return _model_to_dict(model)


@router.patch("/models/{model_name}/status")
async def update_model_status(
    model_name: str,
    req: UpdateStatusRequest,
    version: int | None = Query(default=None),
    user: CurrentUser = Depends(require_roles(Role.DATA_SCIENTIST, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Promote or retire a model."""
    model = _registry.get_model(model_name, version)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    updated = _registry.update_status(model_name, model.version, ModelStatus(req.status))
    return _model_to_dict(updated)


@router.get("/models/{model_name}/compare")
async def compare_model_versions(
    model_name: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Compare all versions of a model."""
    comparison = _registry.compare_models(model_name)
    return {"model_name": model_name, "versions": comparison}


# ── Experiment / Training Endpoints ──────────────────────────────────────────

def _generate_synthetic_data(n_rows: int = 200, n_features: int = 8) -> list[dict[str, Any]]:
    """Generate a synthetic BFSI credit risk dataset for demo experiments."""
    import random
    random.seed(42)
    rows = []
    for _ in range(n_rows):
        age = random.randint(21, 65)
        income = random.randint(200000, 2000000)
        credit_score = random.randint(500, 900)
        loan_amount = random.randint(50000, 5000000)
        ltv = round(loan_amount / (income * 3), 3)
        emi_ratio = round((loan_amount * 0.01) / income, 4)
        existing_loans = random.randint(0, 5)
        delinquencies = random.randint(0, 3)
        # Simple rule-based target for synthetic data
        target = int(
            (credit_score > 700) and
            (emi_ratio < 0.4) and
            (delinquencies < 2) and
            (ltv < 0.8)
        )
        rows.append({
            "age": age,
            "annual_income": income,
            "credit_score": credit_score,
            "loan_amount": loan_amount,
            "loan_to_value": ltv,
            "emi_to_income": emi_ratio,
            "existing_loans": existing_loans,
            "delinquencies_90d": delinquencies,
            "target": target,
        })
    return rows


# Background task logic moved to ExperimentationService


@router.post("/experiments", status_code=status.HTTP_202_ACCEPTED)
async def start_experiment(
    req: ExperimentRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(require_roles(Role.DATA_SCIENTIST, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Launch a training experiment (runs in background, returns experiment ID)."""
    experiment_id = _experiment_service.start_experiment(
        name=req.experiment_name,
        task_type=req.task_type,
        algorithms=req.algorithms,
        data=req.data or _generate_synthetic_data(),
        target_column=req.target_column,
        test_size=req.test_size,
        cv_folds=req.cv_folds,
        created_by=user.email
    )
    
    background_tasks.add_task(
        _experiment_service.run_experiment_background,
        experiment_id=experiment_id,
        name=req.experiment_name,
        task_type=req.task_type,
        algorithms=req.algorithms,
        data=req.data or _generate_synthetic_data(),
        target_column=req.target_column,
        test_size=req.test_size,
        cv_folds=req.cv_folds,
        created_by=user.email
    )
    
    return _experiment_service.get_experiment(experiment_id)


@router.get("/experiments")
async def list_experiments(
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all experiments and their status."""
    experiments = _experiment_service.list_experiments()
    return {
        "experiments": experiments,
        "total": len(experiments),
    }


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the status and results of a specific experiment."""
    exp = _experiment_service.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    return exp


@router.post("/automl/auto", status_code=status.HTTP_200_OK)
async def run_agentic_auto_mode(
    req: AutoMLRequest,
    user: CurrentUser = Depends(require_roles(Role.DATA_SCIENTIST, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Autonomous ML mode: Agent profiles data, chooses algorithm, and trains model.
    
    Returns the final state of the agentic workflow.
    """
    try:
        # Run the workflow synchronously for now (or wrap in background task if long)
        # For a truly responsive UI, we should return a job ID.
        # But for this MVP, we'll run it and return the result.
        result_state = run_auto_mode(req.dataset_id, req.dataset_path, req.target_column)
        return dict(result_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agentic workflow failed: {str(e)}")


# ── Summary endpoint for dashboard ───────────────────────────────────────────

@router.get("/summary")
async def get_ml_summary(
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Aggregate ML metrics for the dashboard."""
    all_models = _registry.list_models()
    all_experiments = _experiment_service.list_experiments()
    deployed = [m for m in all_models if m.status == ModelStatus.DEPLOYED]
    drift_alerts = [
        m for m in all_models if m.tags.get("drift", "none") not in ("none",)
    ]
    best_f1 = max(
        (m.metrics.get("f1", 0) for m in all_models), default=0
    )
    return {
        "total_models": len(all_models),
        "deployed": len(deployed),
        "experiments": len(all_experiments),
        "drift_alerts": len(drift_alerts),
        "best_f1": round(best_f1, 3) if best_f1 else None,
    }


# ── Monitoring & Drift Endpoints ───────────────────────────────────────────

@router.post("/monitoring/log", status_code=status.HTTP_201_CREATED)
async def log_prediction(
    req: PredictionLogRequest,
    db: SessionLocal = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.DATA_SCIENTIST, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Log a model prediction for monitoring."""
    log_id = _monitor.log_prediction(
        db=db,
        model_id=req.model_id,
        features=req.features,
        prediction=req.prediction,
        metadata=req.metadata
    )
    return {"status": "logged", "log_id": log_id}


@router.post("/monitoring/logs/{log_id}/actuals")
async def update_actual(
    log_id: str,
    req: ActualValueRequest,
    db: SessionLocal = Depends(get_db),
    user: CurrentUser = Depends(require_roles(Role.DATA_SCIENTIST, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Update a prediction log with its corresponding ground truth."""
    updated = _monitor.update_actual(db, log_id, req.actual_value)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Log ID '{log_id}' not found")
    return {"status": "updated", "log_id": log_id}


@router.get("/monitoring/{model_id}/drift")
async def check_drift(
    model_id: str,
    window_days: int = Query(default=7, ge=1, le=90),
    db: SessionLocal = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Calculate data drift for a specific model over a time window."""
    try:
        report = _monitor.check_drift(db, model_id, window_days)
        # Update registry tag if drift is detected
        if report.get("drift_detected"):
            model = _registry.get_model_by_id(model_id)
            if model:
                tags = model.tags.copy()
                tags["drift"] = "moderate" if any(f["is_drifted"] for f in report["feature_drifts"].values()) else "none"
                # Simple logic for now: if drift detected, tag it
                _registry.update_tags(model.name, model.version, tags)
        
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drift calculation failed: {str(e)}")
