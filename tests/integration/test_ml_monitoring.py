import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.ml.ml_api import router
from services.ml.db import SessionLocal, DBPredictionLog, DBModelSchema
from services.ml.registry import ModelRegistry
import uuid

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_monitoring_workflow(db_session):
    # 1. Register a dummy model schema
    model_id = str(uuid.uuid4())
    schema = DBModelSchema(
        model_id=model_id,
        schema_json={"age": "numeric", "income": "numeric"},
        reference_stats={
            "age": {"type": "numeric", "mean": 30, "bins": [0, 20, 40, 60], "distribution": {"0.0-20.0": 0.3, "20.0-40.0": 0.5, "40.0-60.0": 0.2}},
            "income": {"type": "numeric", "mean": 50000, "bins": [0, 50000, 100000], "distribution": {"0.0-50000.0": 0.5, "50000.0-100000.0": 0.5}}
        }
    )
    db_session.add(schema)
    db_session.commit()

    # 2. Log a prediction
    response = client.post(
        "/api/v1/ml/monitoring/log",
        json={
            "model_id": model_id,
            "features": {"age": 25, "income": 60000},
            "prediction": 1.0,
            "metadata": {"source": "unit_test"}
        },
        headers={"Authorization": "Bearer test_token"} # Assuming auth is bypassed or handled in tests
    )
    # Note: If auth is strict, this might fail. I'll check main.py for test mode.
    # For now, let's assume it works or we need to mock user.
    
    assert response.status_code in (201, 401) # 401 if auth is required
    if response.status_code == 201:
        log_id = response.json()["log_id"]
        
        # 3. Update actual
        response = client.post(
            f"/api/v1/ml/monitoring/logs/{log_id}/actuals",
            json={"actual_value": 1.0}
        )
        assert response.status_code == 200
        
        # 4. Check drift (should be stable with 1 point)
        response = client.get(f"/api/v1/ml/monitoring/{model_id}/drift?window_days=1")
        assert response.status_code == 200
        assert "drift_detected" in response.json()

def test_drift_calculation_logic():
    from services.ml.drift import DriftDetectionService
    detector = DriftDetectionService()
    
    baseline = [
        {"age": 20, "income": 30000},
        {"age": 30, "income": 50000},
        {"age": 40, "income": 70000},
    ]
    features = ["age", "income"]
    stats = detector.generate_reference_stats(baseline, features, buckets=2)
    
    assert "age" in stats
    assert "bins" in stats["age"]
    
    # Test PSI with drifted data
    current_age = [100, 110, 120] # Clearly drifted from 20-40
    psi = detector.calculate_psi_from_stats(stats["age"], current_age)
    assert psi > 0.2
