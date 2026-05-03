"""Experimentation Service — manages ML experiments lifecycle with PostgreSQL persistence."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from services.ml.db import SessionLocal, DBExperiment
from services.ml.training import TrainingConfig, TrainingService
from services.ml.registry import ModelRegistry
from services.ml.monitoring import MonitoringService
from services.ml.drift import DriftDetectionService


class ExperimentationService:
    """Manages ML experiments, background training, and results tracking."""

    def __init__(self, registry: ModelRegistry, trainer: TrainingService, monitor: MonitoringService):
        self.registry = registry
        self.trainer = trainer
        self.monitor = monitor
        self.drift_detector = DriftDetectionService()

    def start_experiment(
        self,
        name: str,
        task_type: str,
        algorithms: List[str],
        data: Optional[List[dict]] = None,
        target_column: str = "target",
        test_size: float = 0.2,
        cv_folds: int = 5,
        created_by: str = "",
        reasoning: Optional[str] = None,
        trace: Optional[list] = None
    ) -> str:
        """Create an experiment record and return the ID."""
        db: Session = SessionLocal()
        try:
            experiment_id = uuid.uuid4()
            db_exp = DBExperiment(
                experiment_id=experiment_id,
                experiment_name=name,
                task_type=task_type,
                status="queued",
                algorithms=algorithms,
                cv_folds=cv_folds,
                reasoning=reasoning,
                trace=trace,
                created_at=datetime.now(timezone.utc),
            )
            db.add(db_exp)
            db.commit()
            return str(experiment_id)
        finally:
            db.close()

    async def run_experiment_background(
        self,
        experiment_id: str,
        name: str,
        task_type: str,
        algorithms: List[str],
        data: List[dict],
        target_column: str = "target",
        test_size: float = 0.2,
        cv_folds: int = 5,
        created_by: str = ""
    ) -> None:
        """Background task: train models, register them, and update experiment status."""
        db: Session = SessionLocal()
        try:
            # Update status to running
            db_exp = db.query(DBExperiment).filter(DBExperiment.experiment_id == experiment_id).first()
            if not db_exp:
                return
            
            db_exp.status = "running"
            db.commit()

            config = TrainingConfig(
                project_id=str(experiment_id),
                experiment_name=name,
                task_type=task_type,  # type: ignore
                target_column=target_column,
                algorithms=algorithms,
                test_size=test_size,
                cv_folds=cv_folds,
            )

            # Run training in a thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            trained_models = await loop.run_in_executor(None, self.trainer.train, data, config)

            results = []
            registered_ids = []

            for tm in trained_models:
                metrics_dict = {
                    k: v for k, v in {
                        "f1": tm.metrics.f1_score,
                        "auc": tm.metrics.roc_auc,
                        "accuracy": tm.metrics.accuracy,
                        "precision": tm.metrics.precision,
                        "recall": tm.metrics.recall,
                        "cv_mean": tm.metrics.cv_mean,
                        "training_time_s": tm.metrics.training_time_seconds,
                        "r2": tm.metrics.r2_score,
                        "rmse": tm.metrics.rmse,
                    }.items() if v is not None
                }

                registered = self.registry.register(
                    name=f"{name}_{tm.algorithm}",
                    model_object=tm.model_object,
                    algorithm=tm.algorithm,
                    metrics=metrics_dict,
                    feature_names=tm.feature_names,
                    hyperparameters={str(k): str(v) for k, v in tm.hyperparameters.items()},
                    tags={
                        "experiment_id": str(experiment_id),
                        "drift": "none",
                        "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    },
                    created_by=created_by,
                )
                
                # Baseline Drift Stats Calculation & Schema Registration
                # Blueprint §3.4: Automate baseline capture during training.
                try:
                    baseline_stats = self.drift_detector.generate_reference_stats(
                        data=data,
                        features=tm.feature_names
                    )
                    self.monitor.register_schema(
                        db=db,
                        model_id=str(registered.model_id),
                        schema=registered.feature_schema,
                        reference_stats=baseline_stats
                    )
                except Exception as monitor_err:
                    print(f"Monitoring registration failed for {registered.model_id}: {monitor_err}")

                registered_ids.append(str(registered.model_id))
                results.append({
                    "model_id": str(registered.model_id),
                    "algorithm": tm.algorithm,
                    "metrics": metrics_dict,
                })

            # Update status to completed
            db_exp = db.query(DBExperiment).filter(DBExperiment.experiment_id == experiment_id).first()
            db_exp.status = "completed"
            db_exp.results = {
                "models": results,
                "registered_model_ids": registered_ids
            }
            db_exp.completed_at = datetime.now(timezone.utc)
            db.commit()

        except Exception as e:
            # Re-fetch session if needed or just use current
            db_exp = db.query(DBExperiment).filter(DBExperiment.experiment_id == experiment_id).first()
            if db_exp:
                db_exp.status = "failed"
                db_exp.error = str(e)
                db_exp.completed_at = datetime.now(timezone.utc)
                db.commit()
            print(f"Experiment {experiment_id} failed: {e}")
        finally:
            db.close()

    def get_experiment(self, experiment_id: str) -> Optional[dict]:
        """Retrieve experiment details from the database."""
        db: Session = SessionLocal()
        try:
            db_exp = db.query(DBExperiment).filter(DBExperiment.experiment_id == experiment_id).first()
            if not db_exp:
                return None
            
            return {
                "experiment_id": str(db_exp.experiment_id),
                "experiment_name": db_exp.experiment_name,
                "task_type": db_exp.task_type,
                "status": db_exp.status,
                "algorithms": db_exp.algorithms,
                "cv_folds": db_exp.cv_folds,
                "results": db_exp.results or {},
                "error": db_exp.error,
                "reasoning": db_exp.reasoning,
                "trace": db_exp.trace,
                "created_at": db_exp.created_at.isoformat() if db_exp.created_at else None,
                "completed_at": db_exp.completed_at.isoformat() if db_exp.completed_at else None,
            }
        finally:
            db.close()

    def list_experiments(self) -> List[dict]:
        """List all experiments from the database."""
        db: Session = SessionLocal()
        try:
            db_exps = db.query(DBExperiment).order_by(desc(DBExperiment.created_at)).all()
            return [
                {
                    "experiment_id": str(e.experiment_id),
                    "experiment_name": e.experiment_name,
                    "task_type": e.task_type,
                    "status": e.status,
                    "algorithms": e.algorithms,
                    "cv_folds": e.cv_folds,
                    "results": e.results or {},
                    "error": e.error,
                    "reasoning": e.reasoning,
                    "trace": e.trace,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                }
                for e in db_exps
            ]
        finally:
            db.close()

    def run_experiment_sync(
        self,
        name: str,
        dataset_path: str,
        target_column: str,
        algorithm: str,
        params: dict[str, Any],
        task_type: str = "binary_classification",
        reasoning: Optional[str] = None,
        trace: Optional[list] = None
    ) -> dict[str, Any]:
        """Synchronous wrapper for agentic training.
        
        Loads data from CSV and runs training immediately.
        """
        import pandas as pd
        try:
            df = pd.read_csv(dataset_path)
            data = df.to_dict(orient="records")
            
            # Start experiment record
            experiment_id = self.start_experiment(
                name=name,
                task_type=task_type,
                algorithms=[algorithm],
                target_column=target_column,
                created_by="AutoMLAgent",
                reasoning=reasoning,
                trace=trace
            )
            
            # Run training
            config = TrainingConfig(
                project_id=experiment_id,
                experiment_name=name,
                task_type=task_type,
                target_column=target_column,
                algorithms=[algorithm],
            )
            
            trained_models = self.trainer.train(data, config)
            
            if not trained_models:
                return {"error": "Training produced no models"}
                
            tm = trained_models[0]
            
            # Register
            registered = self.registry.register(
                name=f"{name}_{tm.algorithm}",
                model_object=tm.model_object,
                algorithm=tm.algorithm,
                metrics={k: v for k, v in tm.metrics.__dict__.items() if v is not None and not k.startswith("_")},
                feature_names=tm.feature_names,
                hyperparameters={str(k): str(v) for k, v in tm.hyperparameters.items()},
                tags={"experiment_id": experiment_id, "agentic": "true"},
                created_by="AutoMLAgent"
            )
            
            return {
                "experiment_id": experiment_id,
                "model_id": str(registered.model_id),
                "algorithm": tm.algorithm,
                "metrics": registered.metrics
            }
        except Exception as e:
            return {"error": str(e)}
