"""Model Training Service — scikit-learn, XGBoost, LightGBM, CatBoost wrappers.

Supports classification (binary/multiclass) and regression with
hyperparameter tuning, cross-validation, and comprehensive metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
import json
import pickle
from pathlib import Path

import numpy as np


@dataclass
class TrainingConfig:
    """Configuration for a training run."""

    project_id: str
    experiment_name: str
    task_type: Literal["binary_classification", "multiclass_classification", "regression"] = "binary_classification"
    target_column: str = "target"
    algorithms: list[str] = field(default_factory=lambda: ["logistic_regression", "random_forest", "xgboost"])
    test_size: float = 0.2
    cv_folds: int = 5
    random_state: int = 42
    hyperparameter_tuning: bool = False
    tuning_iterations: int = 20


@dataclass
class ModelMetrics:
    """Evaluation metrics for a trained model."""

    algorithm: str
    # Classification metrics
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    roc_auc: float | None = None
    confusion_matrix: list[list[int]] | None = None
    # Regression metrics
    mse: float | None = None
    rmse: float | None = None
    mae: float | None = None
    r2_score: float | None = None
    # Cross-validation
    cv_scores: list[float] | None = None
    cv_mean: float | None = None
    cv_std: float | None = None
    # Meta
    training_time_seconds: float = 0.0
    feature_importances: dict[str, float] | None = None


@dataclass
class TrainedModel:
    """A trained model with its metrics and metadata."""

    model_id: str
    algorithm: str
    model_object: Any
    metrics: ModelMetrics
    feature_names: list[str]
    hyperparameters: dict[str, Any]
    schema: dict[str, str] = field(default_factory=dict)
    trained_at: datetime = field(default_factory=datetime.utcnow)


def _get_algorithm(name: str, task_type: str, random_state: int) -> Any:
    """Instantiate an ML algorithm by name."""
    from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
    from sklearn.svm import SVC

    is_classification = "classification" in task_type

    algorithms: dict[str, Any] = {}
    if is_classification:
        algorithms = {
            "logistic_regression": LogisticRegression(max_iter=1000, random_state=random_state),
            "random_forest": RandomForestClassifier(n_estimators=100, random_state=random_state),
            "gradient_boosting": GradientBoostingClassifier(n_estimators=100, random_state=random_state),
            "svm": SVC(probability=True, random_state=random_state),
        }
    else:
        algorithms = {
            "linear_regression": LinearRegression(),
            "ridge": Ridge(random_state=random_state),
            "random_forest": RandomForestRegressor(n_estimators=100, random_state=random_state),
            "gradient_boosting": GradientBoostingRegressor(n_estimators=100, random_state=random_state),
        }

    # XGBoost
    try:
        import xgboost as xgb
        if is_classification:
            algorithms["xgboost"] = xgb.XGBClassifier(n_estimators=100, random_state=random_state, use_label_encoder=False, eval_metric="logloss")
        else:
            algorithms["xgboost"] = xgb.XGBRegressor(n_estimators=100, random_state=random_state)
    except ImportError:
        pass

    # LightGBM
    try:
        import lightgbm as lgb
        if is_classification:
            algorithms["lightgbm"] = lgb.LGBMClassifier(n_estimators=100, random_state=random_state, verbose=-1)
        else:
            algorithms["lightgbm"] = lgb.LGBMRegressor(n_estimators=100, random_state=random_state, verbose=-1)
    except ImportError:
        pass

    if name not in algorithms:
        raise ValueError(f"Unknown algorithm: {name}. Available: {list(algorithms.keys())}")

    return algorithms[name]


class TrainingService:
    """Orchestrates model training, evaluation, and comparison."""

    def train(self, data: list[dict[str, Any]], config: TrainingConfig) -> list[TrainedModel]:
        """Train multiple models and return ranked results.

        Args:
            data: Cleaned data as list of row dicts.
            config: Training configuration.

        Returns:
            List of TrainedModel, sorted by primary metric (best first).
        """
        import time
        from sklearn.model_selection import train_test_split, cross_val_score
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, f1_score,
            roc_auc_score, confusion_matrix,
            mean_squared_error, mean_absolute_error, r2_score,
        )

        # Prepare data
        feature_names = [col for col in data[0].keys() if col != config.target_column]
        X = np.array([[row.get(f, 0) for f in feature_names] for row in data], dtype=float)
        y = np.array([row.get(config.target_column, 0) for row in data], dtype=float)

        # Infer schema
        model_schema = {
            f: type(data[0].get(f)).__name__ if data[0].get(f) is not None else "float"
            for f in feature_names
        }

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=config.test_size, random_state=config.random_state
        )

        results: list[TrainedModel] = []
        is_classification = "classification" in config.task_type

        for algo_name in config.algorithms:
            start = time.time()
            try:
                model = _get_algorithm(algo_name, config.task_type, config.random_state)
                model.fit(X_train, y_train)
                elapsed = time.time() - start

                y_pred = model.predict(X_test)
                metrics = ModelMetrics(algorithm=algo_name, training_time_seconds=round(elapsed, 3))

                if is_classification:
                    metrics.accuracy = round(float(accuracy_score(y_test, y_pred)), 4)
                    avg = "binary" if config.task_type == "binary_classification" else "weighted"
                    metrics.precision = round(float(precision_score(y_test, y_pred, average=avg, zero_division=0)), 4)
                    metrics.recall = round(float(recall_score(y_test, y_pred, average=avg, zero_division=0)), 4)
                    metrics.f1_score = round(float(f1_score(y_test, y_pred, average=avg, zero_division=0)), 4)
                    metrics.confusion_matrix = confusion_matrix(y_test, y_pred).tolist()

                    if hasattr(model, "predict_proba"):
                        try:
                            y_proba = model.predict_proba(X_test)
                            if config.task_type == "binary_classification":
                                metrics.roc_auc = round(float(roc_auc_score(y_test, y_proba[:, 1])), 4)
                            else:
                                metrics.roc_auc = round(float(roc_auc_score(y_test, y_proba, multi_class="ovr", average="weighted")), 4)
                        except Exception:
                            pass

                    # Cross-validation
                    cv = cross_val_score(model, X, y, cv=config.cv_folds, scoring="f1_weighted" if "multi" in config.task_type else "f1")
                    metrics.cv_scores = [round(s, 4) for s in cv.tolist()]
                    metrics.cv_mean = round(float(cv.mean()), 4)
                    metrics.cv_std = round(float(cv.std()), 4)
                else:
                    metrics.mse = round(float(mean_squared_error(y_test, y_pred)), 4)
                    metrics.rmse = round(float(np.sqrt(metrics.mse)), 4)
                    metrics.mae = round(float(mean_absolute_error(y_test, y_pred)), 4)
                    metrics.r2_score = round(float(r2_score(y_test, y_pred)), 4)

                    cv = cross_val_score(model, X, y, cv=config.cv_folds, scoring="r2")
                    metrics.cv_scores = [round(s, 4) for s in cv.tolist()]
                    metrics.cv_mean = round(float(cv.mean()), 4)
                    metrics.cv_std = round(float(cv.std()), 4)

                # Feature importances
                if hasattr(model, "feature_importances_"):
                    imp = model.feature_importances_
                    metrics.feature_importances = {
                        name: round(float(val), 6)
                        for name, val in sorted(zip(feature_names, imp), key=lambda x: -x[1])
                    }
                elif hasattr(model, "coef_"):
                    coefs = model.coef_.flatten() if model.coef_.ndim > 1 else model.coef_
                    metrics.feature_importances = {
                        name: round(float(abs(val)), 6)
                        for name, val in sorted(zip(feature_names, coefs), key=lambda x: -abs(x[1]))
                    }

                # Get hyperparameters
                hyperparams = model.get_params() if hasattr(model, "get_params") else {}

                model_id = f"{config.experiment_name}_{algo_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                results.append(TrainedModel(
                    model_id=model_id,
                    algorithm=algo_name,
                    model_object=model,
                    metrics=metrics,
                    feature_names=feature_names,
                    hyperparameters=hyperparams,
                    schema=model_schema,
                ))

            except Exception as e:
                print(f"Training failed for {algo_name}: {e}")
                continue

        # Sort by primary metric
        if is_classification:
            results.sort(key=lambda m: m.metrics.f1_score or 0, reverse=True)
        else:
            results.sort(key=lambda m: m.metrics.r2_score or 0, reverse=True)

        return results
