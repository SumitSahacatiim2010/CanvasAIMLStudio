"""Tool Definitions — callable tools for credit decisioning agents.

Blueprint §12: Each tool wraps an external service or internal module.
LangGraph agents call these tools during workflow execution.
Stubbed implementations for Phase 4 — real integrations in later phases.
"""

from datetime import datetime
from typing import Any
import random


def _trace_entry(tool_name: str, details: dict[str, Any]) -> dict[str, Any]:
    """Create a trace entry for audit logging."""
    return {
        "agent": "tool",
        "action": tool_name,
        "timestamp": datetime.utcnow().isoformat(),
        "details": details,
    }


# ── Tool: Credit Risk Scoring ────────────────────────────


def score_credit_risk(applicant_data: dict[str, Any], product_type: str = "personal_loan") -> dict[str, Any]:
    """Score credit risk using the ML model scoring API.

    In production, this calls the ML Platform's prediction endpoint.
    Currently returns a stubbed response for workflow development.
    """
    # Stub: simulate ML model scoring
    base_score = 650
    if applicant_data.get("monthly_income", 0) > 100000:
        base_score += 50
    if applicant_data.get("employment_years", 0) > 5:
        base_score += 30
    if applicant_data.get("existing_loans", 0) > 3:
        base_score -= 40

    score = min(max(base_score + random.randint(-20, 20), 300), 900)
    pd_estimate = max(0.001, 1.0 - (score - 300) / 600)

    grade_map = {range(800, 901): "A", range(700, 800): "B", range(600, 700): "C", range(500, 600): "D"}
    grade = "E"
    for r, g in grade_map.items():
        if score in r:
            grade = g
            break

    return {
        "credit_score": score,
        "probability_of_default": round(pd_estimate, 4),
        "risk_grade": grade,
        "model_version": "v1.0-stub",
        "risk_drivers": [
            {"feature": "income_stability", "contribution": 0.25, "direction": "positive"},
            {"feature": "debt_to_income", "contribution": 0.20, "direction": "negative"},
            {"feature": "credit_history_length", "contribution": 0.15, "direction": "positive"},
        ],
    }


# ── Tool: OCR Processing ─────────────────────────────────


def run_ocr(document: dict[str, Any]) -> dict[str, Any]:
    """Extract text and structured data from documents via OCR.

    In production, uses Tesseract (on-prem) or cloud OCR APIs.
    """
    doc_type = document.get("doc_type", "unknown")

    # Stub: return structured data based on document type
    if doc_type == "salary_slip":
        return {
            "doc_id": document.get("doc_id", ""),
            "extracted_text": "Salary Slip - Employee Name: John Doe...",
            "structured_data": {
                "employee_name": "John Doe",
                "gross_salary": 85000,
                "net_salary": 72000,
                "employer": "Acme Corp",
                "month": "March 2026",
            },
            "confidence": 0.92,
            "pages_processed": 1,
        }
    elif doc_type == "bank_statement":
        return {
            "doc_id": document.get("doc_id", ""),
            "extracted_text": "Bank Statement - Account No: XXXXX1234...",
            "structured_data": {
                "account_number": "XXXXX1234",
                "bank_name": "SBI",
                "period": "Jan-Mar 2026",
                "avg_balance": 245000,
                "total_credits": 255000,
                "total_debits": 198000,
                "bounced_checks": 0,
            },
            "confidence": 0.89,
            "pages_processed": 4,
        }
    else:
        return {
            "doc_id": document.get("doc_id", ""),
            "extracted_text": f"Document content for {doc_type}...",
            "structured_data": {},
            "confidence": 0.75,
            "pages_processed": 1,
        }


# ── Tool: Bureau Query ───────────────────────────────────


def query_bureau(applicant_id: str, bureau: str = "CIBIL") -> dict[str, Any]:
    """Query credit bureau for applicant's credit history.

    Stubbed — in production, calls bureau API with response caching.
    """
    return {
        "bureau": bureau,
        "applicant_id": applicant_id,
        "credit_score": 742,
        "score_date": "2026-04-15",
        "active_loans": [
            {"type": "home_loan", "outstanding": 2500000, "emi": 22000, "dpd_current": 0},
            {"type": "credit_card", "outstanding": 45000, "limit": 200000, "dpd_current": 0},
        ],
        "closed_loans": 3,
        "total_enquiries_6m": 2,
        "max_dpd_12m": 0,
        "max_dpd_24m": 15,
        "oldest_account_years": 8,
        "write_offs": 0,
    }


# ── Tool: Policy Evaluation ──────────────────────────────


def evaluate_policy(
    applicant_data: dict[str, Any],
    risk_scores: dict[str, Any],
    product_type: str = "personal_loan",
) -> dict[str, Any]:
    """Evaluate application against policy rules.

    Delegates to the PolicyEngine for full rule evaluation.
    See services/agentic/policy_engine.py for rule definitions.
    """
    from services.agentic.policy_engine import PolicyEngine

    engine = PolicyEngine()
    return engine.evaluate(applicant_data, risk_scores, product_type)


# ── Tool: RAG Knowledge Search ───────────────────────────


def search_knowledge_base(query: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Search the RAG knowledge base for relevant documents.

    In production, calls the RAG retrieval API (Phase 5).
    """
    return {
        "query": query,
        "results": [
            {
                "doc_id": "REG-001",
                "title": "RBI Master Direction on Lending",
                "section": "§4.2 — Income Assessment Guidelines",
                "relevance_score": 0.91,
                "snippet": "Lenders must verify income through at least two independent sources...",
            },
            {
                "doc_id": "POL-005",
                "title": "Internal Credit Policy v3.2",
                "section": "§7 — Personal Loan Eligibility",
                "relevance_score": 0.87,
                "snippet": "Minimum CIBIL score of 650 required for personal loan applications...",
            },
        ],
        "total_results": 2,
    }


# ── Tool: Collateral Valuation ───────────────────────────


def assess_collateral(collateral_data: dict[str, Any]) -> dict[str, Any]:
    """Assess collateral value and LTV ratio.

    Stubbed — in production, integrates with valuation APIs.
    """
    declared_value = collateral_data.get("declared_value", 0)
    collateral_type = collateral_data.get("type", "property")

    # Apply haircuts based on type
    haircuts = {"property": 0.85, "vehicle": 0.70, "fixed_deposit": 0.95, "gold": 0.80}
    haircut = haircuts.get(collateral_type, 0.75)
    assessed_value = declared_value * haircut

    return {
        "collateral_type": collateral_type,
        "declared_value": declared_value,
        "assessed_value": round(assessed_value),
        "haircut_applied": haircut,
        "legal_status": "clear",
        "insurance_status": "valid",
        "valuation_date": datetime.utcnow().strftime("%Y-%m-%d"),
    }


# ── Tool Registry ────────────────────────────────────────

TOOL_REGISTRY: dict[str, Any] = {
    "score_credit_risk": score_credit_risk,
    "run_ocr": run_ocr,
    "query_bureau": query_bureau,
    "evaluate_policy": evaluate_policy,
    "search_knowledge_base": search_knowledge_base,
    "assess_collateral": assess_collateral,
}
