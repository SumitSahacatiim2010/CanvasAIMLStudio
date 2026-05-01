"""Agentic Workflow API — REST endpoints for credit decisioning.

Exposes the LangGraph workflow as HTTP endpoints for submitting applications,
executing workflows, and managing maker-checker reviews.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from services.gateway.app.auth import CurrentUser, Role, get_current_user, require_roles
from services.agentic.workflow import run_credit_decisioning, generate_decision_card
from services.agentic.state import ReviewStatus

router = APIRouter(prefix="/api/v1/agentic", tags=["Credit Decisioning"])


# ── Pydantic Models ──────────────────────────────────────


class ApplicationSubmit(BaseModel):
    """Submit a new loan application."""

    applicant_name: str = Field(..., min_length=1)
    age: int = Field(..., ge=18, le=80)
    monthly_income: float = Field(..., gt=0)
    employment_years: float = Field(default=0, ge=0)
    employment_months: int = Field(default=0, ge=0)
    existing_loans: int = Field(default=0, ge=0)
    total_emi: float = Field(default=0, ge=0)
    requested_amount: float = Field(..., gt=0)
    requested_tenor_years: int = Field(default=3, ge=1, le=30)
    product_type: str = Field(default="personal_loan")
    segment: str = Field(default="retail")
    geography: str = Field(default="IN")
    declared_income: float | None = None


class MakerReview(BaseModel):
    """Maker review decision."""

    decision: str = Field(..., pattern="^(approve|reject|escalate)$")
    justification: str = Field(..., min_length=10)
    conditions: list[str] = Field(default_factory=list)


class CheckerReview(BaseModel):
    """Checker review decision."""

    decision: str = Field(..., pattern="^(approve|reject|send_back)$")
    justification: str = Field(..., min_length=10)


# ── In-Memory Application Store ──────────────────────────

_applications: dict[str, dict[str, Any]] = {}
_app_counter = 0


# ── Endpoints ────────────────────────────────────────────


@router.post("/applications", status_code=status.HTTP_201_CREATED)
async def submit_application(
    app: ApplicationSubmit,
    user: CurrentUser = Depends(require_roles(Role.BUSINESS_USER, Role.DATA_SCIENTIST, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Submit a loan application and run the decisioning workflow."""
    global _app_counter
    _app_counter += 1
    app_id = f"APP-{_app_counter:06d}"

    applicant_data = {
        "name": app.applicant_name,
        "age": app.age,
        "monthly_income": app.monthly_income,
        "declared_income": app.declared_income or app.monthly_income,
        "employment_years": app.employment_years,
        "employment_months": app.employment_months or int(app.employment_years * 12),
        "existing_loans": app.existing_loans,
        "total_emi": app.total_emi,
        "requested_amount": app.requested_amount,
        "requested_tenor_years": app.requested_tenor_years,
    }

    # Run the workflow
    final_state = run_credit_decisioning(
        application_id=app_id,
        applicant_data=applicant_data,
        product_type=app.product_type,
        segment=app.segment,
        geography=app.geography,
    )

    # Store the state
    _applications[app_id] = final_state

    # Return decision card
    card = generate_decision_card(final_state)
    card["submitted_by"] = user.email
    return card


@router.get("/applications")
async def list_applications(
    status_filter: str | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all applications with summary info."""
    apps = []
    for app_id, state in _applications.items():
        summary = {
            "application_id": app_id,
            "applicant": state.get("applicant_data", {}).get("name", "Unknown"),
            "product": state.get("product_type"),
            "decision": state.get("decision"),
            "risk_grade": state.get("risk_grade"),
            "review_status": state.get("review_status"),
            "submitted_at": state.get("started_at"),
        }
        if status_filter and summary["decision"] != status_filter:
            continue
        apps.append(summary)
    return {"applications": apps, "total": len(apps)}


@router.get("/applications/{app_id}")
async def get_application(
    app_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get full application details including decision card and trace."""
    if app_id not in _applications:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found")

    state = _applications[app_id]
    card = generate_decision_card(state)
    card["trace"] = state.get("trace", [])
    card["policy_details"] = state.get("policy_results", {}).get("details", [])
    card["income_analysis"] = state.get("income_analysis", {})
    card["bureau_data"] = state.get("bureau_data", {})
    return card


@router.get("/applications/{app_id}/trace")
async def get_application_trace(
    app_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the workflow execution trace for an application."""
    if app_id not in _applications:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found")

    state = _applications[app_id]
    return {
        "application_id": app_id,
        "trace": state.get("trace", []),
        "errors": state.get("errors", []),
        "total_duration_ms": sum(t.get("duration_ms", 0) for t in state.get("trace", [])),
    }


# ── Maker-Checker Endpoints ─────────────────────────────


@router.post("/applications/{app_id}/maker-review")
async def submit_maker_review(
    app_id: str,
    review: MakerReview,
    user: CurrentUser = Depends(require_roles(Role.RISK_OFFICER, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Submit maker review for an application."""
    if app_id not in _applications:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found")

    state = _applications[app_id]

    if state.get("review_status") != ReviewStatus.PENDING_MAKER.value:
        raise HTTPException(status_code=400, detail=f"Application not in pending maker review state")

    state["maker_review"] = {
        "reviewer_id": user.user_id,
        "reviewer_email": user.email,
        "decision": review.decision,
        "justification": review.justification,
        "conditions": review.conditions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if review.decision == "approve":
        state["review_status"] = ReviewStatus.PENDING_CHECKER.value
    elif review.decision == "reject":
        state["review_status"] = ReviewStatus.MAKER_REJECTED.value
        state["decision"] = "rejected"
        state["decision_rationale"] += f" | Maker rejected: {review.justification}"
    elif review.decision == "escalate":
        state["review_status"] = "escalated"

    return {
        "application_id": app_id,
        "review_status": state["review_status"],
        "maker_decision": review.decision,
    }


@router.post("/applications/{app_id}/checker-review")
async def submit_checker_review(
    app_id: str,
    review: CheckerReview,
    user: CurrentUser = Depends(require_roles(Role.RISK_OFFICER, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Submit checker review to finalize the decision."""
    if app_id not in _applications:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found")

    state = _applications[app_id]

    if state.get("review_status") != ReviewStatus.PENDING_CHECKER.value:
        raise HTTPException(status_code=400, detail=f"Application not in pending checker review state")

    # Prevent same person from being maker and checker
    maker_id = state.get("maker_review", {}).get("reviewer_id", "")
    if maker_id == user.user_id:
        raise HTTPException(status_code=403, detail="Checker cannot be the same person as maker")

    state["checker_review"] = {
        "reviewer_id": user.user_id,
        "reviewer_email": user.email,
        "decision": review.decision,
        "justification": review.justification,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if review.decision == "approve":
        state["review_status"] = ReviewStatus.FINALIZED.value
    elif review.decision == "reject":
        state["review_status"] = ReviewStatus.CHECKER_REJECTED.value
        state["decision"] = "rejected"
        state["decision_rationale"] += f" | Checker rejected: {review.justification}"
    elif review.decision == "send_back":
        state["review_status"] = ReviewStatus.PENDING_MAKER.value
        state["checker_review"]["note"] = "Sent back to maker for re-review"

    return {
        "application_id": app_id,
        "review_status": state["review_status"],
        "checker_decision": review.decision,
        "final_decision": state.get("decision"),
    }
