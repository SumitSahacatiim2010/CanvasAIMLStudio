"""AutoML Agent — The autonomous brain of CanvasMLStudio.

Blueprint §4: Agents are autonomous entities that make decisions.
In the AutoML context, this agent 'looks' at data and 'selects' the best
ML strategy, mimicking a human ML engineer.
"""

from datetime import datetime
from typing import Any
from services.agentic.state import AutoMLState
from services.agentic.automl_tools import profile_dataset, execute_training_plan

def automl_planner_agent(state: AutoMLState) -> AutoMLState:
    """The planning node of the AutoML workflow.
    
    Acts as an ML Architect:
    1. Profiles the data.
    2. Reasons about the best algorithm.
    3. Sets hyperparameters.
    """
    start_time = datetime.utcnow()
    
    # 1. Profile Data
    profile = profile_dataset(state["dataset_path"])
    if "error" in profile:
        state["errors"].append({"node": "automl_planner", "error": profile["error"]})
        return state
        
    state["schema"] = profile["schema"]
    state["baseline_stats"] = profile["statistics"]
    
    # 2. Logic / Reasoning (Mocking LLM decision process)
    # In production, this would call an LLM with the profile data in the prompt.
    
    target_col = state.get("target_column") or (profile["target_candidates"][0] if profile["target_candidates"] else None)
    if not target_col:
        # Fallback: assume last column is target
        target_col = list(profile["schema"].keys())[-1]
    
    state["target_column"] = target_col
    
    # Determine problem type based on target dtype
    target_dtype = profile["schema"][target_col]
    if "float" in target_dtype.lower():
        state["problem_type"] = "regression"
        state["algorithm"] = "random_forest"  # RF is robust for regression
        state["reasoning"] = f"Target '{target_col}' is float. Selecting Random Forest Regression for robustness."
    else:
        state["problem_type"] = "classification"
        # Intelligent selection based on row count
        if profile["row_count"] > 1000:
            state["algorithm"] = "xgboost"
            state["reasoning"] = f"Dataset has {profile['row_count']} rows. Selecting XGBoost for high-performance classification."
        else:
            state["algorithm"] = "logistic_regression"
            state["reasoning"] = f"Small dataset ({profile['row_count']} rows). Selecting Logistic Regression for interpretability and to avoid overfitting."

    # 3. Set Hyperparameters (Agentically determined)
    state["hyperparameters"] = {
        "n_estimators": 100 if state["algorithm"] != "logistic_regression" else None,
        "max_depth": 5 if state["algorithm"] == "xgboost" else None,
        "random_state": 42
    }
    
    # 4. Update Trace
    duration = (datetime.utcnow() - start_time).total_seconds() * 1000
    state["trace"].append({
        "node": "automl_planner",
        "action": "analyze_and_plan",
        "duration_ms": duration,
        "details": {
            "chosen_algorithm": state["algorithm"],
            "reasoning": state["reasoning"]
        }
    })
    
    return state

def automl_execution_agent(state: AutoMLState) -> AutoMLState:
    """The execution node of the AutoML workflow.
    
    Acts as an ML Operator:
    Takes the plan and triggers the training engine.
    """
    start_time = datetime.utcnow()
    
    if not state.get("algorithm"):
        return state
        
    # Trigger training
    result = execute_training_plan(
        dataset_path=state["dataset_path"],
        target_column=state["target_column"],
        algorithm=state["algorithm"],
        params=state["hyperparameters"],
        task_type=state.get("problem_type", "binary_classification"),
        reasoning=state.get("reasoning"),
        trace=state.get("trace")
    )
    
    if "error" in result:
        state["errors"].append({"node": "automl_execution", "error": result["error"]})
    else:
        state["experiment_id"] = result.get("experiment_id")
        state["model_id"] = result.get("model_id")
        state["metrics"] = result.get("metrics", {})
        
    # Update Trace
    duration = (datetime.utcnow() - start_time).total_seconds() * 1000
    state["trace"].append({
        "node": "automl_execution",
        "action": "execute_training",
        "duration_ms": duration,
        "details": {
            "experiment_id": state.get("experiment_id"),
            "model_id": state.get("model_id")
        }
    })
    
    state["completed_at"] = datetime.utcnow().isoformat()
    return state
