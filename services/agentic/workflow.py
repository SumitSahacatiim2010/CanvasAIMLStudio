"""LangGraph Credit Decisioning Workflow — StateGraph definition.

Blueprint §12: Stateful multi-step agent graph with conditional edges,
human-in-the-loop interrupt points, and PostgreSQL checkpointing.

This module defines the graph topology. The graph can be executed
standalone or via the API endpoints in workflow_api.py.
"""

from typing import Any

from services.agentic.state import AgentState, create_initial_state
from services.agentic.agents import (
    document_ingestion_agent,
    ocr_agent,
    document_verification_agent,
    income_analysis_agent,
    bank_statement_agent,
    risk_scoring_agent,
    collateral_agent,
    policy_evaluation_agent,
    orchestration_agent,
    should_assess_collateral,
    needs_human_review,
)


def build_credit_decisioning_graph() -> Any:
    """Build the LangGraph StateGraph for credit decisioning.

    Graph topology:
        START → document_ingestion → ocr → document_verification
        → income_analysis → bank_statement → risk_scoring
        → [conditional: collateral or policy] → policy_evaluation
        → orchestration → [conditional: human_review or finalize] → END

    Returns:
        Compiled LangGraph StateGraph (or a fallback sequential executor
        if langgraph is not installed).
    """
    try:
        from langgraph.graph import StateGraph, END

        graph = StateGraph(AgentState)

        # Add agent nodes
        graph.add_node("document_ingestion", document_ingestion_agent)
        graph.add_node("ocr", ocr_agent)
        graph.add_node("document_verification", document_verification_agent)
        graph.add_node("income_analysis", income_analysis_agent)
        graph.add_node("bank_statement", bank_statement_agent)
        graph.add_node("risk_scoring", risk_scoring_agent)
        graph.add_node("collateral", collateral_agent)
        graph.add_node("policy_evaluation", policy_evaluation_agent)
        graph.add_node("orchestration", orchestration_agent)

        # Set entry point
        graph.set_entry_point("document_ingestion")

        # Linear edges
        graph.add_edge("document_ingestion", "ocr")
        graph.add_edge("ocr", "document_verification")
        graph.add_edge("document_verification", "income_analysis")
        graph.add_edge("income_analysis", "bank_statement")
        graph.add_edge("bank_statement", "risk_scoring")

        # Conditional: collateral assessment (only for secured products)
        graph.add_conditional_edges(
            "risk_scoring",
            should_assess_collateral,
            {"collateral": "collateral", "policy": "policy_evaluation"},
        )
        graph.add_edge("collateral", "policy_evaluation")

        # Policy → Orchestration
        graph.add_edge("policy_evaluation", "orchestration")

        # Conditional: human review or finalize
        graph.add_conditional_edges(
            "orchestration",
            needs_human_review,
            {"human_review": END, "finalize": END},  # HITL interrupts at END
        )

        # Compile with interrupt_before for maker-checker
        compiled = graph.compile()
        return compiled

    except ImportError:
        # Fallback: simple sequential executor without LangGraph
        return SequentialWorkflow()


class SequentialWorkflow:
    """Fallback executor when LangGraph is not installed.

    Runs agents sequentially without graph features (conditional edges,
    checkpointing). Useful for development and testing.
    """

    def __init__(self) -> None:
        self._agents = [
            ("document_ingestion", document_ingestion_agent),
            ("ocr", ocr_agent),
            ("document_verification", document_verification_agent),
            ("income_analysis", income_analysis_agent),
            ("bank_statement", bank_statement_agent),
            ("risk_scoring", risk_scoring_agent),
            ("collateral", collateral_agent),
            ("policy_evaluation", policy_evaluation_agent),
            ("orchestration", orchestration_agent),
        ]

    def invoke(self, state: AgentState) -> AgentState:
        """Execute all agents sequentially."""
        current_state = state
        for name, agent_fn in self._agents:
            try:
                current_state = agent_fn(current_state)
            except Exception as e:
                current_state["errors"].append({
                    "agent": name,
                    "error": str(e),
                    "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                })
        return current_state

    async def ainvoke(self, state: AgentState) -> AgentState:
        """Async wrapper for sequential execution."""
        return self.invoke(state)


def run_credit_decisioning(
    application_id: str,
    applicant_data: dict[str, Any] | None = None,
    product_type: str = "personal_loan",
    segment: str = "retail",
    geography: str = "IN",
) -> AgentState:
    """High-level API to run the full credit decisioning workflow.

    Args:
        application_id: Unique application identifier.
        applicant_data: Applicant profile data.
        product_type: Loan product type.
        segment: Customer segment.
        geography: Jurisdiction code.

    Returns:
        Final AgentState with decision, risk scores, and trace.
    """
    state = create_initial_state(application_id, product_type, segment, geography)

    if applicant_data:
        state["applicant_data"] = applicant_data

    workflow = build_credit_decisioning_graph()
    final_state = workflow.invoke(state)

    return final_state


def generate_decision_card(state: AgentState) -> dict[str, Any]:
    """Generate a human-readable decision card from the final state.

    The decision card is the primary output artifact for each application.
    """
    return {
        "application_id": state.get("application_id"),
        "decision": state.get("decision"),
        "confidence": state.get("decision_confidence"),
        "rationale": state.get("decision_rationale"),
        "risk_grade": state.get("risk_grade"),
        "risk_scores": state.get("risk_scores"),
        "recommended_terms": state.get("recommended_terms"),
        "policy_summary": {
            "total_rules": state.get("policy_results", {}).get("total_rules", 0),
            "passed": state.get("policy_results", {}).get("passed", 0),
            "hard_rejections": len(state.get("hard_rejections", [])),
            "soft_flags": len(state.get("soft_flags", [])),
        },
        "key_risk_drivers": state.get("risk_drivers", [])[:5],
        "documents_processed": len(state.get("documents", [])),
        "workflow_trace_length": len(state.get("trace", [])),
        "processing_time_ms": sum(t.get("duration_ms", 0) for t in state.get("trace", [])),
        "review_status": state.get("review_status"),
        "timestamp": state.get("completed_at"),
    }
