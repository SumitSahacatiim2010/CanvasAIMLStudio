"""Model Registry — versioned artefact storage, metrics tracking, lifecycle management.

Stores trained models with their metadata, metrics, and deployment status.
Supports local filesystem storage (Phase 0) and S3/MinIO (Phase 1+).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
import json
import pickle


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
    """Manages model lifecycle from training to retirement.

    Storage layout:
        registry_path/
        ├── {model_name}/
        │   ├── v1/
        │   │   ├── model.pkl
        │   │   └── metadata.json
        │   ├── v2/
        │   │   ├── model.pkl
        │   │   └── metadata.json
        │   └── latest -> v2
        └── registry.json  (index of all models)
    """

    def __init__(self, registry_path: str = "./model_registry") -> None:
        self.path = Path(registry_path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._models: dict[str, list[RegisteredModel]] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load registry index from disk."""
        index_path = self.path / "registry.json"
        if index_path.exists():
            with open(index_path, "r") as f:
                data = json.load(f)
                for entry in data.get("models", []):
                    model = RegisteredModel(
                        model_id=entry["model_id"],
                        name=entry["name"],
                        version=entry["version"],
                        algorithm=entry["algorithm"],
                        status=ModelStatus(entry["status"]),
                        artifact_path=entry["artifact_path"],
                        metrics=entry.get("metrics", {}),
                        hyperparameters=entry.get("hyperparameters", {}),
                        feature_names=entry.get("feature_names", []),
                        feature_schema=entry.get("feature_schema", {}),
                        tags=entry.get("tags", {}),
                        created_by=entry.get("created_by", ""),
                    )
                    if model.name not in self._models:
                        self._models[model.name] = []
                    self._models[model.name].append(model)

    def _save_index(self) -> None:
        """Save registry index to disk."""
        all_models = []
        for versions in self._models.values():
            for m in versions:
                all_models.append({
                    "model_id": m.model_id,
                    "name": m.name,
                    "version": m.version,
                    "algorithm": m.algorithm,
                    "status": m.status.value,
                    "artifact_path": m.artifact_path,
                    "metrics": m.metrics,
                    "hyperparameters": {k: str(v) for k, v in m.hyperparameters.items()},
                    "feature_names": m.feature_names,
                    "feature_schema": m.feature_schema,
                    "tags": m.tags,
                    "created_by": m.created_by,
                    "created_at": m.created_at.isoformat(),
                })

        index_path = self.path / "registry.json"
        with open(index_path, "w") as f:
            json.dump({"models": all_models, "updated_at": datetime.utcnow().isoformat()}, f, indent=2)

    def register(
        self,
        name: str,
        model_object: Any,
        algorithm: str,
        metrics: dict[str, Any],
        feature_names: list[str],
        hyperparameters: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
        created_by: str = "",
    ) -> RegisteredModel:
        """Register a trained model in the registry.

        Automatically versions the model (v1, v2, ...).
        Serializes the model object to disk.
        """
        # Determine version
        existing = self._models.get(name, [])
        version = len(existing) + 1

        # Create storage directory
        model_dir = self.path / name / f"v{version}"
        model_dir.mkdir(parents=True, exist_ok=True)

        # Save model artifact
        artifact_path = str(model_dir / "model.pkl")
        with open(artifact_path, "wb") as f:
            pickle.dump(model_object, f)

        # Save metadata
        model_id = f"{name}_v{version}"
        feature_schema = {fn: "numeric" for fn in feature_names}  # Default; refined by profiling

        registered = RegisteredModel(
            model_id=model_id,
            name=name,
            version=version,
            algorithm=algorithm,
            status=ModelStatus.TRAINED,
            artifact_path=artifact_path,
            metrics=metrics,
            hyperparameters=hyperparameters or {},
            feature_names=feature_names,
            feature_schema=feature_schema,
            tags=tags or {},
            created_by=created_by,
        )

        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump({
                "model_id": registered.model_id,
                "name": name,
                "version": version,
                "algorithm": algorithm,
                "metrics": metrics,
                "feature_names": feature_names,
                "created_at": registered.created_at.isoformat(),
            }, f, indent=2)

        if name not in self._models:
            self._models[name] = []
        self._models[name].append(registered)
        self._save_index()

        return registered

    def get_model(self, name: str, version: int | None = None) -> RegisteredModel | None:
        """Get a registered model by name and version (latest if version is None)."""
        versions = self._models.get(name, [])
        if not versions:
            return None
        if version is None:
            return versions[-1]
        return next((m for m in versions if m.version == version), None)

    def load_model(self, name: str, version: int | None = None) -> Any:
        """Load a model object from the registry."""
        registered = self.get_model(name, version)
        if not registered:
            raise ValueError(f"Model not found: {name} v{version}")
        with open(registered.artifact_path, "rb") as f:
            return pickle.load(f)  # noqa: S301

    def list_models(self, status: ModelStatus | None = None) -> list[RegisteredModel]:
        """List all registered models, optionally filtered by status."""
        all_models = [m for versions in self._models.values() for m in versions]
        if status:
            all_models = [m for m in all_models if m.status == status]
        return all_models

    def update_status(self, name: str, version: int, new_status: ModelStatus) -> RegisteredModel | None:
        """Update model lifecycle status."""
        model = self.get_model(name, version)
        if model:
            model.status = new_status
            model.updated_at = datetime.utcnow()
            self._save_index()
        return model

    def compare_models(self, name: str) -> list[dict[str, Any]]:
        """Compare all versions of a model by their metrics."""
        versions = self._models.get(name, [])
        return [
            {"version": m.version, "algorithm": m.algorithm, "status": m.status.value, "metrics": m.metrics}
            for m in versions
        ]
