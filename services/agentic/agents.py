"""Agent Nodes — individual processing steps in the credit decisioning graph.

Blueprint §4: Each agent is a function that takes AgentState and returns
an updated AgentState. Agents call tools and record trace entries.
"""

from datetime import datetime
from typing import Any
import time

from services.agentic.state import AgentState, DecisionOutcome
from services.agentic.tools import (
    run_ocr,
    query_bureau,
    score_credit_risk,
    assess_collateral,
    search_knowledge_base,
)


def _add_trace(state: AgentState, agent: str, action: str, details: dict[str, Any], duration_ms: float) -> None:
    """Append a trace entry to the state."""
    state["trace"].append({
        "agent": agent,
        "action": action,
        "timestamp": datetime.utcnow().isoformat(),
        "duration_ms": round(duration_ms, 1),
        "details": details,
    })


# ── Agent 1: Document Ingestion ──────────────────────────

def document_ingestion_agent(state: AgentState) -> AgentState:
    """Receive and register documents for the application."""
    start = time.time()

    # In production, this reads from the document upload queue
    if not state.get("documents"):
        state["documents"] = [
            {"doc_id": "DOC-001", "doc_type": "salary_slip", "file_path": "/uploads/salary.pdf", "status": "received"},
            {"doc_id": "DOC-002", "doc_type": "bank_statement", "file_path": "/uploads/bank.pdf", "status": "received"},
            {"doc_id": "DOC-003", "doc_type": "id_proof", "file_path": "/uploads/aadhar.pdf", "status": "received"},
        ]

    for doc in state["documents"]:
        doc["status"] = "ingested"

    elapsed = (time.time() - start) * 1000
    _add_trace(state, "DocumentIngestionAgent", "ingest_documents",
               {"count": len(state["documents"])}, elapsed)
    return state


# ── Agent 2: OCR Processing ──────────────────────────────

def ocr_agent(state: AgentState) -> AgentState:
    """Extract text and structured data from documents using OCR."""
    start = time.time()

    ocr_results: dict[str, Any] = {}
    for doc in state.get("documents", []):
        result = run_ocr(doc)
        ocr_results[doc["doc_id"]] = result
        doc["status"] = "ocr_completed"

    state["ocr_results"] = ocr_results

    elapsed = (time.time() - start) * 1000
    _add_trace(state, "OCRAgent", "extract_text",
               {"documents_processed": len(ocr_results)}, elapsed)
    return state


# ── Agent 3: Document Verification ───────────────────────

def document_verification_agent(state: AgentState) -> AgentState:
    """Verify document authenticity and cross-check extracted data."""
    start = time.time()

    verification: dict[str, Any] = {}
    for doc_id, ocr in state.get("ocr_results", {}).items():
        # Stub verification logic
        confidence = ocr.get("confidence", 0)
        verification[doc_id] = {
            "verified": confidence > 0.8,
            "confidence": confidence,
            "tampering_score": 0.02,  # Low = good
            "issues": [] if confidence > 0.8 else ["Low OCR confidence"],
        }

    state["document_verification"] = verification

    elapsed = (time.time() - start) * 1000
    _add_trace(state, "DocumentVerificationAgent", "verify_documents",
               {"verified": sum(1 for v in verification.values() if v["verified"]),
                "total": len(verification)}, elapsed)
    return state


# ── Agent 4: Income Analysis ─────────────────────────────

def income_analysis_agent(state: AgentState) -> AgentState:
    """Analyze income from salary slips and other documents."""
    start = time.time()

    salary_data = {}
    for doc_id, ocr in state.get("ocr_results", {}).items():
        if "salary" in str(state.get("documents", [{}])):
            salary_data = ocr.get("structured_data", {})

    # Extract from OCR results
    for doc_id, ocr in state.get("ocr_results", {}).items():
        sd = ocr.get("structured_data", {})
        if sd.get("gross_salary"):
            salary_data = sd

    gross = salary_data.get("gross_salary", state.get("applicant_data", {}).get("monthly_income", 50000))
    declared = state.get("applicant_data", {}).get("declared_income", gross)

    state["income_analysis"] = {
        "declared_income": declared,
        "verified_income": gross,
        "income_source": salary_data.get("employer", "Unknown"),
        "income_stability": "stable",
        "dti_ratio": round(state.get("applicant_data", {}).get("total_emi", 15000) / max(gross, 1), 4),
        "foir": round(state.get("applicant_data", {}).get("total_emi", 15000) / max(gross, 1), 4),
    }

    # Update applicant data with verified info
    state["applicant_data"]["verified_income"] = gross
    state["applicant_data"]["dti_ratio"] = state["income_analysis"]["dti_ratio"]

    elapsed = (time.time() - start) * 1000
    _add_trace(state, "IncomeAnalysisAgent", "analyze_income",
               {"verified_income": gross, "dti": state["income_analysis"]["dti_ratio"]}, elapsed)
    return state


# ── Agent 5: Bank Statement Analysis ─────────────────────

def bank_statement_agent(state: AgentState) -> AgentState:
    """Analyze bank statements for cash flow patterns."""
    start = time.time()

    bank_data = {}
    for doc_id, ocr in state.get("ocr_results", {}).items():
        sd = ocr.get("structured_data", {})
        if sd.get("avg_balance"):
            bank_data = sd

    state["bank_statement_analysis"] = {
        "avg_balance": bank_data.get("avg_balance", 150000),
        "total_credits": bank_data.get("total_credits", 255000),
        "total_debits": bank_data.get("total_debits", 198000),
        "net_cash_flow": bank_data.get("total_credits", 255000) - bank_data.get("total_debits", 198000),
        "bounced_checks": bank_data.get("bounced_checks", 0),
        "emi_obligations_detected": 2,
        "cash_flow_stability": "stable",
    }

    elapsed = (time.time() - start) * 1000
    _add_trace(state, "BankStatementAgent", "analyze_bank_statement",
               {"avg_balance": state["bank_statement_analysis"]["avg_balance"]}, elapsed)
    return state


# ── Agent 6: Risk Scoring ────────────────────────────────

def risk_scoring_agent(state: AgentState) -> AgentState:
    """Score credit risk using ML models and bureau data."""
    start = time.time()

    # Query bureau
    bureau = query_bureau(state.get("application_id", ""), "CIBIL")
    state["bureau_data"] = bureau

    # Score with ML model
    scoring_result = score_credit_risk(state.get("applicant_data", {}), state.get("product_type", ""))

    state["risk_scores"] = {
        "ml_model_score": scoring_result["credit_score"],
        "bureau_score": bureau["credit_score"],
        "blended_score": round((scoring_result["credit_score"] * 0.4 + bureau["credit_score"] * 0.6)),
        "probability_of_default": scoring_result["probability_of_default"],
    }
    state["risk_grade"] = scoring_result["risk_grade"]
    state["risk_drivers"] = scoring_result["risk_drivers"]

    elapsed = (time.time() - start) * 1000
    _add_trace(state, "RiskScoringAgent", "score_risk",
               {"blended_score": state["risk_scores"]["blended_score"],
                "grade": state["risk_grade"]}, elapsed)
    return state


# ── Agent 7: Collateral Assessment ───────────────────────

def collateral_agent(state: AgentState) -> AgentState:
    """Assess collateral if applicable (secured loans)."""
    start = time.time()

    if state.get("product_type") in ("home_loan", "secured_business_loan"):
        collateral_input = state.get("collateral_data", {"type": "property", "declared_value": 5000000})
        state["collateral_data"] = assess_collateral(collateral_input)
        state["applicant_data"]["ltv_ratio"] = round(
            state.get("applicant_data", {}).get("requested_amount", 3500000) /
            max(state["collateral_data"].get("assessed_value", 1), 1), 4
        )
    else:
        state["collateral_data"] = {"type": "unsecured", "assessed_value": 0, "legal_status": "n/a"}

    elapsed = (time.time() - start) * 1000
    _add_trace(state, "CollateralAgent", "assess_collateral",
               {"type": state["collateral_data"].get("type")}, elapsed)
    return state


# ── Agent 8: Policy Evaluation ───────────────────────────

def policy_evaluation_agent(state: AgentState) -> AgentState:
    """Evaluate application against all policy rules."""
    start = time.time()

    from services.agentic.policy_engine import PolicyEngine

    engine = PolicyEngine()
    merged_data = {**state.get("applicant_data", {}), **state.get("income_analysis", {})}
    merged_risk = {**state.get("risk_scores", {}), **state.get("bureau_data", {})}

    result = engine.evaluate(merged_data, merged_risk, state.get("product_type", "personal_loan"))

    state["policy_results"] = result
    state["hard_rejections"] = result.get("hard_rejections", [])
    state["soft_flags"] = result.get("soft_flags", [])

    elapsed = (time.time() - start) * 1000
    _add_trace(state, "PolicyEvaluationAgent", "evaluate_policy",
               {"rules_evaluated": result["total_rules"],
                "hard_rejections": len(state["hard_rejections"]),
                "soft_flags": len(state["soft_flags"])}, elapsed)
    return state


# ── Agent 9: Orchestration / Decision ────────────────────

def orchestration_agent(state: AgentState) -> AgentState:
    """Make the final credit decision based on all collected data.

    Decision logic:
    1. If any hard rejections → auto-reject
    2. If risk grade D/E and soft flags → refer to manual
    3. If soft flags present → approve with conditions (requires maker review)
    4. If all clear → auto-approve
    """
    start = time.time()

    # Decision logic
    if state.get("hard_rejections"):
        state["decision"] = DecisionOutcome.REJECTED.value
        state["decision_confidence"] = 0.95
        state["decision_rationale"] = (
            f"Application auto-rejected due to {len(state['hard_rejections'])} policy violation(s): "
            + "; ".join(state["hard_rejections"][:3])
        )

    elif state.get("risk_grade") in ("D", "E") and state.get("soft_flags"):
        state["decision"] = DecisionOutcome.REFERRED.value
        state["decision_confidence"] = 0.6
        state["decision_rationale"] = (
            f"High risk (grade {state['risk_grade']}) with {len(state.get('soft_flags', []))} "
            f"concern(s). Requires manual underwriter review."
        )

    elif state.get("soft_flags"):
        state["decision"] = DecisionOutcome.APPROVED.value
        state["decision_confidence"] = 0.75
        state["decision_rationale"] = (
            f"Conditionally approved. {len(state['soft_flags'])} item(s) flagged for review: "
            + "; ".join(state["soft_flags"][:3])
        )

    else:
        state["decision"] = DecisionOutcome.APPROVED.value
        state["decision_confidence"] = 0.90
        state["decision_rationale"] = (
            f"Auto-approved. Risk grade: {state.get('risk_grade', 'N/A')}. "
            f"All {state.get('policy_results', {}).get('total_rules', 0)} policy rules passed."
        )

    # Recommended terms
    blended = state.get("risk_scores", {}).get("blended_score", 700)
    requested = state.get("applicant_data", {}).get("requested_amount", 500000)
    base_rate = 10.5  # base lending rate
    spread = max(0, (800 - blended) * 0.02)  # higher risk = higher rate

    state["recommended_terms"] = {
        "approved_amount": requested if state["decision"] == "approved" else 0,
        "interest_rate": round(base_rate + spread, 2),
        "tenor_months": state.get("applicant_data", {}).get("requested_tenor_years", 3) * 12,
        "processing_fee_pct": 1.5,
        "conditions": state.get("soft_flags", []),
    }

    state["completed_at"] = datetime.utcnow().isoformat()

    elapsed = (time.time() - start) * 1000
    _add_trace(state, "OrchestrationAgent", "make_decision",
               {"decision": state["decision"], "confidence": state["decision_confidence"],
                "grade": state.get("risk_grade")}, elapsed)
    return state


# ── Routing Functions ────────────────────────────────────

def should_assess_collateral(state: AgentState) -> str:
    """Route: if secured product, go to collateral; otherwise skip to policy."""
    if state.get("product_type") in ("home_loan", "secured_business_loan"):
        return "collateral"
    return "policy"


def needs_human_review(state: AgentState) -> str:
    """Route: after decision, determine if HITL review is needed."""
    decision = state.get("decision", "")
    if decision == DecisionOutcome.REJECTED.value:
        return "finalize"  # Auto-rejections don't need maker-checker
    return "human_review"  # Approvals and referrals need maker-checker
