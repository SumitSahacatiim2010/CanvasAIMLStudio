import pytest
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime, timezone
from services.ml.monitoring import MonitoringService
from services.ml.db import DBPredictionLog, DBModelSchema, DBModel

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def monitor():
    return MonitoringService()

def test_log_prediction_logic(monitor, mock_db):
    model_id = str(uuid.uuid4())
    prediction_id = "test-pred-1"
    features = {"age": 25, "income": 50000}
    prediction = 0.8
    
    # Mock get_schema to return None (skip validation)
    with patch.object(monitor, "get_schema", return_value=None):
        monitor.log_prediction(
            db=mock_db,
            model_id=model_id,
            prediction_id=prediction_id,
            input_features=features,
            prediction=prediction,
            latency_ms=15.5
        )
    
    # Verify DB calls
    assert mock_db.add.called
    log_entry = mock_db.add.call_args[0][0]
    assert isinstance(log_entry, DBPredictionLog)
    assert log_entry.prediction_id == prediction_id
    assert log_entry.latency_ms == 15.5
    assert mock_db.commit.called

def test_drift_analysis_logic(monitor, mock_db):
    model_id = str(uuid.uuid4())
    m_uuid = uuid.UUID(model_id)
    
    # Mock schema
    mock_schema = DBModelSchema(
        model_id=m_uuid,
        schema_json={"age": "numeric"},
        reference_stats={"age": {"type": "numeric", "mean": 30, "bins": [0, 50], "distribution": {"0-50": 1.0}}}
    )
    
    # Mock logs
    mock_log = DBPredictionLog(
        model_id=m_uuid,
        input_features={"age": 35},
        prediction=0.7,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Configure mock_db behavior
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_schema, MagicMock()] # schema, then model
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_log]
    
    # Run analysis
    report = monitor.perform_drift_analysis(mock_db, model_id)
    
    assert report is not None
    assert hasattr(report, "drift_status")
    assert mock_db.commit.called
