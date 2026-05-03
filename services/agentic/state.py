"""Agent State — typed state definition for the credit decisioning workflow.

Blueprint §4 + §12: The AgentState flows through a LangGraph StateGraph,
accumulating data as each agent node processes the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypedDict


class DecisionOutcome(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REFERRED = "referred_to_manual"
    PENDING = "pending"
    ESCALATED = "escalated"


class ReviewStatus(str, Enum):
    PENDING_MAKER = "pending_maker_review"
    MAKER_APPROVED = "maker_approved"
    MAKER_REJECTED = "maker_rejected"
    PENDING_CHECKER = "pending_checker_review"
    CHECKER_APPROVED = "checker_approved"
    CHECKER_REJECTED = "checker_rejected"
    FINALIZED = "finalized"


class AgentState(TypedDict, total=False):
    """Typed state for the credit decisioning LangGraph workflow.

    Accumulates data as each agent node processes the loan application.
    """

    # ── Application Identity ─────────────────────────────
    application_id: str
    product_type: str  # home_loan, personal_loan, business_loan, credit_card
    segment: str  # retail, sme, corporate
    geography: str  # jurisdiction code

    # ── Document Processing ──────────────────────────────
    documents: list[dict[str, Any]]  # [{doc_id, doc_type, file_path, status}]
    ocr_results: dict[str, Any]  # {doc_id: {extracted_text, structured_data, confidence}}
    document_verification: dict[str, Any]  # {doc_id: {verified, issues, tampering_score}}

    # ── Extracted & Enriched Data ────────────────────────
    applicant_data: dict[str, Any]  # name, dob, address, employment, etc.
    income_analysis: dict[str, Any]  # declared_income, verified_income, dti_ratio, stability
    bank_statement_analysis: dict[str, Any]  # avg_balance, cash_flows, obligations, bounced_checks
    bureau_data: dict[str, Any]  # credit_score, active_loans, dpd_history, enquiries
    collateral_data: dict[str, Any]  # type, valuation, ltv_ratio, legal_status

    # ── Risk Assessment ──────────────────────────────────
    risk_scores: dict[str, float]  # {model_name: score}
    risk_grade: str  # A, B, C, D, E
    risk_drivers: list[dict[str, Any]]  # [{feature, contribution, direction}]
    xai_explanation: dict[str, Any]  # SHAP values, counterfactuals

    # ── Policy Evaluation ────────────────────────────────
    policy_results: dict[str, Any]  # {rule_name: {passed, reason}}
    hard_rejections: list[str]  # Rules that cause automatic rejection
    soft_flags: list[str]  # Warnings that require human review
    policy_overrides: list[dict[str, Any]]  # Overrides applied by maker/checker

    # ── Decision ─────────────────────────────────────────
    decision: str  # approved, rejected, referred_to_manual
    decision_confidence: float  # 0.0 to 1.0
    decision_rationale: str  # Human-readable explanation
    recommended_terms: dict[str, Any]  # {amount, rate, tenor, conditions}

    # ── Governance ───────────────────────────────────────
    review_status: str  # maker-checker status
    maker_review: dict[str, Any]  # {reviewer_id, decision, justification, timestamp}
    checker_review: dict[str, Any]  # {reviewer_id, decision, justification, timestamp}

    # ── Tracing & Audit ──────────────────────────────────
    trace: list[dict[str, Any]]  # [{agent, action, timestamp, duration_ms, details}]
    errors: list[dict[str, Any]]  # [{agent, error, timestamp}]
    started_at: str
    completed_at: str


class AutoMLState(TypedDict, total=False):
    """Typed state for the AutoML agentic workflow."""
    
    # ── Dataset Identity ───────────────────────────────
    dataset_id: str
    dataset_path: str
    target_column: str
    
    # ── Analysis ────────────────────────────────────────
    schema: dict[str, Any]
    baseline_stats: dict[str, Any]
    feature_importance: dict[str, float]
    
    # ── Decisions ───────────────────────────────────────
    problem_type: str  # classification, regression
    algorithm: str  # xgboost, random_forest, etc.
    hyperparameters: dict[str, Any]
    preprocessing_steps: list[str]
    
    # ── Outcomes ────────────────────────────────────────
    experiment_id: str
    model_id: str
    metrics: dict[str, float]
    reasoning: str  # LLM's rationale for choices
    
    # ── Infrastructure ──────────────────────────────────
    trace: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    started_at: str
    completed_at: str


def create_initial_automl_state(dataset_id: str, dataset_path: str) -> AutoMLState:
    """Create a fresh AutoMLState."""
    return AutoMLState(
        dataset_id=dataset_id,
        dataset_path=dataset_path,
        schema={},
        baseline_stats={},
        feature_importance={},
        hyperparameters={},
        preprocessing_steps=[],
        trace=[],
        errors=[],
        started_at=datetime.utcnow().isoformat(),
        completed_at="",
    )


def create_initial_state(
    application_id: str,
    product_type: str = "personal_loan",
    segment: str = "retail",
    geography: str = "IN",
) -> AgentState:
    """Create a fresh AgentState for a new application."""
    return AgentState(
        application_id=application_id,
        product_type=product_type,
        segment=segment,
        geography=geography,
        documents=[],
        ocr_results={},
        document_verification={},
        applicant_data={},
        income_analysis={},
        bank_statement_analysis={},
        bureau_data={},
        collateral_data={},
        risk_scores={},
        risk_grade="",
        risk_drivers=[],
        xai_explanation={},
        policy_results={},
        hard_rejections=[],
        soft_flags=[],
        policy_overrides=[],
        decision=DecisionOutcome.PENDING.value,
        decision_confidence=0.0,
        decision_rationale="",
        recommended_terms={},
        review_status=ReviewStatus.PENDING_MAKER.value,
        maker_review={},
        checker_review={},
        trace=[],
        errors=[],
        started_at=datetime.utcnow().isoformat(),
        completed_at="",
    )
