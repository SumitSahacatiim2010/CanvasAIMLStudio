# Machine Learning Services (ML Platform)

The ML Platform provides a suite of services for the full ML lifecycle, including training, experimentation, monitoring, and observability.

## Core Services

### 1. Training & Experimentation
- **TrainingService**: Automated model training using scikit-learn. Supports classification and regression tasks.
- **ExperimentationService**: Manages multiple training runs, tracks metrics, and persists results in PostgreSQL.
- **ModelRegistry**: Versioned storage for model artifacts and metadata.

### 2. Monitoring & Observability
- **MonitoringService**: Logs production predictions and latencies. Performs data validation against registered schemas.
- **DriftDetectionService**: Identifies statistical shifts between training and production distributions using PSI (Population Stability Index) and KS (Kolmogorov-Smirnov) tests.
- **Automated Baselines**: Capture baseline distributions during training to enable zero-config drift monitoring.

## Monitoring Workflow

1. **Schema Registration**: Models automatically register their input schema and baseline statistics during training via `ExperimentationService`.
2. **Prediction Logging**: Use `MonitoringService.log_prediction` to record production inference data.
3. **Drift Analysis**: Call `perform_drift_analysis` to generate a report on model and feature drift.

## Database Schema

The ML platform uses PostgreSQL with the following key tables:
- `ml_models`: Metadata and artifact paths for all registered models.
- `ml_experiments`: Tracking for training runs.
- `ml_model_schemas`: Stores input feature types and baseline statistics for drift detection.
- `ml_prediction_logs`: High-performance logging of production inference data.

## Getting Started

To run drift analysis on a model:
```python
from services.ml.monitoring import MonitoringService
from services.ml.db import SessionLocal

monitor = MonitoringService()
db = SessionLocal()
report = monitor.perform_drift_analysis(db, model_id="your-model-uuid")
print(f"Drift Status: {report.drift_status}")
```
