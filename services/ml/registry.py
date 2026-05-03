"""Model Registry — versioned artefact storage, metrics tracking, lifecycle management.

Stores trained models with their metadata, metrics, and deployment status.
Supports local filesystem storage (Phase 0) and S3/MinIO (Phase 1+).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
import json
import pickle
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import desc
from services.ml.db import SessionLocal, DBModel

class ModelStatus(str, Enum):
    TRAINED = "trained"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    RETIRED = "retired"
    FAILED = "failed"


@dataclass
class RegisteredModel:
    """A model registered in the registry."""

    model_id: str
    name: str
    version: int
    algorithm: str
    status: ModelStatus
    artifact_path: str
    metrics: dict[str, Any]
    hyperparameters: dict[str, Any]
    feature_names: list[str]
    feature_schema: dict[str, str]  # {feature_name: dtype}
    tags: dict[str, str] = field(default_factory=dict)
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class ModelRegistry:
    """Manages model lifecycle from training to retirement using PostgreSQL."""

    def __init__(self, registry_path: str = "./model_registry") -> None:
        self.path = Path(registry_path)
        self.path.mkdir(parents=True, exist_ok=True)

    def _db_model_to_dataclass(self, db_model: DBModel) -> RegisteredModel:
        tags = db_model.tags or {}
        feature_names = tags.get("feature_names", [])
        feature_schema = tags.get("feature_schema", {})
        created_by = tags.get("created_by", "")
        
        return RegisteredModel(
            model_id=str(db_model.model_id),
            name=db_model.name,
            version=db_model.version,
            algorithm=db_model.algorithm,
            status=ModelStatus(db_model.status),
            artifact_path=db_model.model_artifact_path,
            metrics=db_model.metrics or {},
            hyperparameters=db_model.hyperparameters or {},
            feature_names=feature_names,
            feature_schema=feature_schema,
            tags=tags,
            created_by=created_by,
            created_at=db_model.trained_at or datetime.now(timezone.utc),
            updated_at=db_model.trained_at or datetime.now(timezone.utc),
        )

    def register(
        self,
        name: str,
        model_object: Any,
        algorithm: str,
        metrics: dict[str, Any],
        feature_names: list[str],
        feature_schema: dict[str, str] | None = None,
        hyperparameters: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
        created_by: str = "",
    ) -> RegisteredModel:
        """Register a trained model in the registry.

        Automatically versions the model (v1, v2, ...).
        Serializes the model object to disk.
        """
        db: Session = SessionLocal()
        try:
            # Determine version
            latest_model = db.query(DBModel).filter(DBModel.name == name).order_by(desc(DBModel.version)).first()
            version = (latest_model.version + 1) if latest_model else 1

            # Create storage directory
            model_dir = self.path / name / f"v{version}"
            model_dir.mkdir(parents=True, exist_ok=True)

            # Save model artifact
            artifact_path = str(model_dir / "model.pkl")
            with open(artifact_path, "wb") as f:
                pickle.dump(model_object, f)

            feature_schema = feature_schema or {fn: "numeric" for fn in feature_names}

            combined_tags = tags or {}
            combined_tags.update({
                "feature_names": feature_names,
                "feature_schema": feature_schema,
                "created_by": created_by
            })

            db_model = DBModel(
                model_id=uuid.uuid4(),
                name=name,
                version=version,
                algorithm=algorithm,
                status=ModelStatus.TRAINED.value,
                model_artifact_path=artifact_path,
                metrics=metrics,
                hyperparameters=hyperparameters or {},
                tags=combined_tags,
                trained_at=datetime.now(timezone.utc)
            )

            db.add(db_model)
            db.commit()
            db.refresh(db_model)

            return self._db_model_to_dataclass(db_model)
        finally:
            db.close()

    def get_model(self, name: str, version: int | None = None) -> RegisteredModel | None:
        """Get a registered model by name and version (latest if version is None)."""
        db: Session = SessionLocal()
        try:
            query = db.query(DBModel).filter(DBModel.name == name)
            if version is not None:
                query = query.filter(DBModel.version == version)
            else:
                query = query.order_by(desc(DBModel.version))
            
            db_model = query.first()
            if not db_model:
                return None
            return self._db_model_to_dataclass(db_model)
        finally:
            db.close()

    def load_model(self, name: str, version: int | None = None) -> Any:
        """Load a model object from the registry."""
        registered = self.get_model(name, version)
        if not registered:
            raise ValueError(f"Model not found: {name} v{version}")
        with open(registered.artifact_path, "rb") as f:
            return pickle.load(f)  # noqa: S301

    def list_models(self, status: ModelStatus | None = None) -> list[RegisteredModel]:
        """List all registered models, optionally filtered by status."""
        db: Session = SessionLocal()
        try:
            query = db.query(DBModel)
            if status:
                query = query.filter(DBModel.status == status.value)
            
            db_models = query.all()
            return [self._db_model_to_dataclass(m) for m in db_models]
        finally:
            db.close()

    def update_status(self, name: str, version: int, new_status: ModelStatus) -> RegisteredModel | None:
        """Update model lifecycle status."""
        db: Session = SessionLocal()
        try:
            db_model = db.query(DBModel).filter(DBModel.name == name, DBModel.version == version).first()
            if db_model:
                db_model.status = new_status.value
                db.commit()
                db.refresh(db_model)
                return self._db_model_to_dataclass(db_model)
            return None
        finally:
            db.close()

    def get_model_by_id(self, model_id: str) -> RegisteredModel | None:
        """Get a registered model by its unique ID."""
        db: Session = SessionLocal()
        try:
            db_model = db.query(DBModel).filter(DBModel.model_id == model_id).first()
            if not db_model:
                return None
            return self._db_model_to_dataclass(db_model)
        finally:
            db.close()

    def update_tags(self, name: str, version: int, tags: dict[str, str]) -> RegisteredModel | None:
        """Update model tags."""
        db: Session = SessionLocal()
        try:
            db_model = db.query(DBModel).filter(DBModel.name == name, DBModel.version == version).first()
            if db_model:
                db_model.tags = tags
                db.commit()
                db.refresh(db_model)
                return self._db_model_to_dataclass(db_model)
            return None
        finally:
            db.close()

    def compare_models(self, name: str) -> list[dict[str, Any]]:
        """Compare all versions of a model by their metrics."""
        db: Session = SessionLocal()
        try:
            db_models = db.query(DBModel).filter(DBModel.name == name).order_by(desc(DBModel.version)).all()
            return [
                {"version": m.version, "algorithm": m.algorithm, "status": m.status, "metrics": m.metrics or {}}
                for m in db_models
            ]
        finally:
            db.close()
