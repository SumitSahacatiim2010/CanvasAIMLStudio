"""AutoML Agentic Workflow — Autonomous ML pipeline.

Blueprint §12: LangGraph workflow for dataset analysis and model training.
"""

from typing import Any
from services.agentic.state import AutoMLState, create_initial_automl_state
from services.agentic.automl_agent import automl_planner_agent, automl_execution_agent

def build_automl_graph() -> Any:
    """Build the LangGraph StateGraph for AutoML.
    
    START → automl_planner → automl_execution → END
    """
    try:
        from langgraph.graph import StateGraph, END
        
        graph = StateGraph(AutoMLState)
        
        graph.add_node("planner", automl_planner_agent)
        graph.add_node("executor", automl_execution_agent)
        
        graph.set_entry_point("planner")
        graph.add_edge("planner", "executor")
        graph.add_edge("executor", END)
        
        return graph.compile()
    except ImportError:
        return SimpleAutoMLWorkflow()

class SimpleAutoMLWorkflow:
    """Fallback sequential executor."""
    def invoke(self, state: AutoMLState) -> AutoMLState:
        state = automl_planner_agent(state)
        state = automl_execution_agent(state)
        return state

def run_auto_mode(dataset_id: str = None, dataset_path: str = "", target_column: str = None) -> AutoMLState:
    """Run the complete Agentic Auto Mode for a dataset."""
    import uuid
    if not dataset_id:
        dataset_id = str(uuid.uuid4())
    state = create_initial_automl_state(dataset_id, dataset_path)
    if target_column:
        state["target_column"] = target_column
        
    workflow = build_automl_graph()
    final_state = workflow.invoke(state)
    
    return final_state
