"""AutoML Agent Tools — capabilities for autonomous ML management.

Blueprint §4: Tools are functions that agents call to perform actions
or retrieve information from the environment.
"""

from typing import Any
import pandas as pd
from services.monitoring.drift import MonitoringService
from services.ml.experimentation import ExperimentationService

def profile_dataset(dataset_path: str) -> dict[str, Any]:
    """Analyze a dataset to retrieve schema and baseline statistics.
    
    This is the primary tool for the AutoML Agent to 'understand' the data.
    """
    try:
        df = pd.read_csv(dataset_path)
        
        # Get schema
        schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        # Use MonitoringService for deep stats
        monitor = MonitoringService()
        stats = monitor.compute_baseline_stats(df)
        
        return {
            "schema": schema,
            "row_count": len(df),
            "column_count": len(df.columns),
            "statistics": stats,
            "missing_values": df.isnull().sum().to_dict(),
            "target_candidates": [col for col in df.columns if col.lower() in ("target", "label", "outcome", "churn", "fraud", "y")]
        }
    except Exception as e:
        return {"error": f"Failed to profile dataset: {str(e)}"}

def execute_training_plan(
    dataset_path: str, 
    target_column: str, 
    algorithm: str, 
    params: dict[str, Any],
    task_type: str = "binary_classification",
    reasoning: Any = None,
    trace: Any = None
) -> dict[str, Any]:
    """Execute an ML training plan suggested by the agent.
    
    This connects the Agent's decision to the ML engine.
    """
    try:
        experiment_service = ExperimentationService()
        
        # In a real system, this would be async. For this MVP, we run synchronously.
        # We need to map agent algorithm names to our TrainingService names.
        algo_map = {
            "xgboost": "XGBoost",
            "random_forest": "RandomForest",
            "logistic_regression": "LogisticRegression",
            "decision_tree": "DecisionTree"
        }
        
        actual_algo = algo_map.get(algorithm.lower(), "RandomForest")
        
        result = experiment_service.run_experiment_sync(
            name=f"Agentic_{actual_algo}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}",
            dataset_path=dataset_path,
            target_column=target_column,
            algorithm=actual_algo,
            params=params,
            task_type=task_type,
            reasoning=reasoning,
            trace=trace
        )
        
        return result
    except Exception as e:
        return {"error": f"Training failed: {str(e)}"}
