"""Monitoring Service — handles prediction logging and health metrics.

Blueprint §3.4: Real-time observability and feedback loops.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from services.ml.db import DBPredictionLog, DBModelSchema, DBModel
from services.ml.drift import DriftDetectionService, DriftReport

class MonitoringService:
    """Service for logging predictions and monitoring model health."""

    def __init__(self):
        self.drift_service = DriftDetectionService()
        self._model_cache = {}  # Cache model metadata (schema, stats)

    def log_prediction(
        self,
        db: Session,
        model_id: str,
        prediction_id: str,
        input_features: Dict[str, Any],
        prediction: Any,
        latency_ms: float = 0.0
    ):
        """Log a single prediction and validate features."""
        # Validate features against schema
        is_valid, error = self.validate_features(db, model_id, input_features)
        
        log_entry = DBPredictionLog(
            model_id=uuid.UUID(model_id) if isinstance(model_id, str) else model_id,
            prediction_id=prediction_id,
            input_features=input_features,
            prediction=prediction,
            latency_ms=latency_ms,
            error=None if is_valid else error
        )
        db.add(log_entry)
        db.commit()

    def validate_features(self, db: Session, model_id: str, features: Dict[str, Any]) -> (bool, Optional[str]):
        """Validate input features against the registered schema."""
        schema = self.get_schema(db, model_id)
        if not schema:
            return True, None  # No schema registered, skip validation
            
        for f_name, f_type in schema.items():
            if f_name not in features:
                return False, f"Missing feature: {f_name}"
            
            val = features[f_name]
            if f_type == "numeric" and not isinstance(val, (int, float)):
                return False, f"Feature {f_name} should be numeric, got {type(val).__name__}"
            elif f_type == "categorical" and not isinstance(val, (str, bool, int)):
                return False, f"Feature {f_name} should be categorical, got {type(val).__name__}"
                
        return True, None

    def log_ground_truth(self, db: Session, prediction_id: str, ground_truth: Any):
        """Update a log entry with ground truth (feedback loop)."""
        log_entry = db.query(DBPredictionLog).filter(DBPredictionLog.prediction_id == prediction_id).first()
        if log_entry:
            log_entry.ground_truth = ground_truth
            db.commit()

    def get_logs(self, db: Session, model_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve logs for a model."""
        m_id = uuid.UUID(model_id) if isinstance(model_id, str) else model_id
        logs = db.query(DBPredictionLog).filter(
            DBPredictionLog.model_id == m_id
        ).order_by(DBPredictionLog.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "id": str(l.id),
                "prediction_id": l.prediction_id,
                "input_features": l.input_features,
                "prediction": l.prediction,
                "ground_truth": l.ground_truth,
                "latency_ms": l.latency_ms,
                "timestamp": l.timestamp.isoformat()
            }
            for l in logs
        ]

    def perform_drift_analysis(
        self, 
        db: Session, 
        model_id: str, 
        reference_data: Optional[List[Dict[str, Any]]] = None
    ) -> DriftReport:
        """Perform drift analysis using recent logs and reference data/stats."""
        m_id = uuid.UUID(model_id) if isinstance(model_id, str) else model_id
        
        # Get schema and reference stats
        db_schema = db.query(DBModelSchema).filter(DBModelSchema.model_id == m_id).first()
        if not db_schema:
            raise ValueError(f"No schema/baseline found for model {model_id}")
            
        features = list(db_schema.schema_json.keys())
        ref_stats = db_schema.reference_stats
        
        # Get last 1000 predictions for analysis
        current_logs = db.query(DBPredictionLog).filter(
            DBPredictionLog.model_id == m_id
        ).order_by(DBPredictionLog.timestamp.desc()).limit(1000).all()
        
        current_data = [l.input_features for l in current_logs]
        
        report = self.drift_service.detect_drift(
            current_data=current_data,
            features=features,
            model_id=model_id,
            reference_data=reference_data,
            reference_stats=ref_stats
        )
        
        # Update model drift status in DB
        model = db.query(DBModel).filter(DBModel.model_id == m_id).first()
        if model:
            model.drift = report.drift_status
            db.commit()
            
        return report

    def register_schema(self, db: Session, model_id: str, schema: Dict[str, str], reference_stats: Optional[Dict[str, Any]] = None):
        """Save model schema and baseline statistics for monitoring."""
        m_id = uuid.UUID(model_id) if isinstance(model_id, str) else model_id
        db_schema = db.query(DBModelSchema).filter(DBModelSchema.model_id == m_id).first()
        if db_schema:
            db_schema.schema_json = schema
            if reference_stats:
                db_schema.reference_stats = reference_stats
        else:
            db_schema = DBModelSchema(model_id=m_id, schema_json=schema, reference_stats=reference_stats)
            db.add(db_schema)
        db.commit()
        
        # Update cache
        self._model_cache[str(m_id)] = {"schema": schema, "stats": reference_stats}

    def get_schema(self, db: Session, model_id: str) -> Optional[Dict[str, str]]:
        """Retrieve model schema, using cache if available."""
        if str(model_id) in self._model_cache:
            return self._model_cache[str(model_id)]["schema"]
            
        m_id = uuid.UUID(model_id) if isinstance(model_id, str) else model_id
        db_schema = db.query(DBModelSchema).filter(DBModelSchema.model_id == m_id).first()
        if db_schema:
            self._model_cache[str(m_id)] = {
                "schema": db_schema.schema_json,
                "stats": db_schema.reference_stats
            }
            return db_schema.schema_json
        return None
