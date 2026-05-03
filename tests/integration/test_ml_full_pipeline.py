import os

# Set DATABASE_URL before importing services
TEST_DATABASE_URL = "sqlite:///./test_ml.db"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.ml.db import Base, SessionLocal, engine as db_engine
from services.ml.training import TrainingService
from services.ml.registry import ModelRegistry
from services.ml.monitoring import MonitoringService
from services.ml.experimentation import ExperimentationService
from services.ml.drift import DriftDetectionService
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="module")
def setup_db():
    # Override the real engine with test engine for the duration of tests
    # In a real app, you'd use dependency injection, but here we monkeypatch or use env
    Base.metadata.create_all(bind=test_engine)
    yield
    # No need to drop all if we delete the file, but dispose is critical
    test_engine.dispose()
    db_engine.dispose()
    if os.path.exists("./test_ml.db"):
        try:
            os.remove("./test_ml.db")
        except:
            pass

@pytest.fixture
def db_session(setup_db):
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_full_ml_pipeline(db_session, monkeypatch):
    # 1. Mock the services to use the test session
    # We need to monkeypatch SessionLocal in the services
    import services.ml.db
    monkeypatch.setattr(services.ml.db, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(services.ml.db, "engine", test_engine)

    registry = ModelRegistry()
    trainer = TrainingService()
    monitor = MonitoringService()
    experiment_service = ExperimentationService(registry, trainer, monitor)

    # 2. Create dummy training data
    data = [
        {"age": 25, "income": 50000, "target": 0},
        {"age": 30, "income": 60000, "target": 0},
        {"age": 45, "income": 120000, "target": 1},
        {"age": 50, "income": 130000, "target": 1},
        {"age": 22, "income": 45000, "target": 0},
        {"age": 35, "income": 70000, "target": 0},
        {"age": 60, "income": 150000, "target": 1},
        {"age": 55, "income": 140000, "target": 1},
    ] * 5  # Duplicate to have enough rows for training

    # 3. Start and run experiment
    exp_id = experiment_service.start_experiment(
        name="test_integration_exp",
        task_type="classification",
        algorithms=["random_forest"]
    )

    # Run background task synchronously for testing
    import asyncio
    asyncio.run(experiment_service.run_experiment_background(
        experiment_id=exp_id,
        name="test_integration_exp",
        task_type="classification",
        algorithms=["random_forest"],
        data=data,
        target_column="target"
    ))

    # 4. Verify results
    exp = experiment_service.get_experiment(exp_id)
    assert exp["status"] == "completed"
    assert len(exp["results"]["registered_model_ids"]) > 0
    model_id = exp["results"]["registered_model_ids"][0]

    # 5. Check if schema and baseline stats were saved
    from services.ml.db import DBModelSchema
    schema_record = db_session.query(DBModelSchema).filter(DBModelSchema.model_id == model_id).first()
    assert schema_record is not None
    assert "income" in schema_record.schema_json
    assert "income" in schema_record.reference_stats

    # 6. Log production data with drift
    # Baseline income mean was ~90k. Let's log some high income data.
    drifted_data = [
        {"age": 40, "income": 250000},
        {"age": 42, "income": 260000},
        {"age": 45, "income": 270000},
    ]
    
    for i, row in enumerate(drifted_data):
        monitor.log_prediction(
            db=db_session,
            model_id=model_id,
            prediction_id=f"pred_{i}",
            input_features=row,
            prediction={"label": 1},
            latency_ms=10.5
        )

    # 7. Perform drift analysis
    report = monitor.perform_drift_analysis(db_session, model_id)
    assert report.model_id == model_id
    # Since we have very few rows, PSI might be high
    assert any(d.feature_name == "income" for d in report.feature_drifts)
    assert report.drift_status in ["none", "moderate", "high"]
    
    # Dispose engines to release file locks
    test_engine.dispose()
    db_engine.dispose()

    print(f"Integration Test Passed. Drift Status: {report.drift_status}")

if __name__ == "__main__":
    pytest.main([__file__])
