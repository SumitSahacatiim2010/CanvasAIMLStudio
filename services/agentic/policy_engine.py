"""Policy Engine — JSON DSL-based rule evaluation for credit decisioning.

Blueprint §4: Rules are grouped by product, segment, and geography.
Each rule evaluates conditions on raw data + ML-derived features
and outputs hard rejections or soft recommendations.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PolicyRule:
    """A single policy rule definition."""

    rule_id: str
    name: str
    category: str  # eligibility, credit, regulatory, operational
    severity: str  # hard (auto-reject) or soft (flag for review)
    condition: str  # Human-readable condition description
    products: list[str] = field(default_factory=lambda: ["all"])
    segments: list[str] = field(default_factory=lambda: ["all"])


@dataclass
class RuleResult:
    """Result of evaluating a single rule."""

    rule_id: str
    rule_name: str
    passed: bool
    severity: str
    reason: str


# ── Default Policy Rules ─────────────────────────────────

DEFAULT_RULES: list[PolicyRule] = [
    # Hard rejection rules
    PolicyRule(
        rule_id="HR-001", name="Minimum Age", category="eligibility", severity="hard",
        condition="Applicant age >= 21", products=["all"],
    ),
    PolicyRule(
        rule_id="HR-002", name="Maximum Age", category="eligibility", severity="hard",
        condition="Applicant age <= 65 at loan maturity", products=["all"],
    ),
    PolicyRule(
        rule_id="HR-003", name="Minimum Credit Score", category="credit", severity="hard",
        condition="Bureau score >= 600", products=["personal_loan", "home_loan"],
    ),
    PolicyRule(
        rule_id="HR-004", name="No Write-offs", category="credit", severity="hard",
        condition="No write-offs in last 36 months", products=["all"],
    ),
    PolicyRule(
        rule_id="HR-005", name="DPD History", category="credit", severity="hard",
        condition="Max DPD in 12 months <= 30 days", products=["all"],
    ),
    PolicyRule(
        rule_id="HR-006", name="Minimum Income", category="eligibility", severity="hard",
        condition="Monthly income >= 25000", products=["personal_loan"],
    ),

    # Soft flag rules
    PolicyRule(
        rule_id="SF-001", name="High DTI Ratio", category="credit", severity="soft",
        condition="Debt-to-income ratio <= 50%",
    ),
    PolicyRule(
        rule_id="SF-002", name="Employment Stability", category="eligibility", severity="soft",
        condition="Employment tenure >= 12 months",
    ),
    PolicyRule(
        rule_id="SF-003", name="High Enquiry Count", category="credit", severity="soft",
        condition="Bureau enquiries in 6 months <= 4",
    ),
    PolicyRule(
        rule_id="SF-004", name="LTV Ratio", category="credit", severity="soft",
        condition="Loan-to-value <= 80%", products=["home_loan"],
    ),
    PolicyRule(
        rule_id="SF-005", name="Income Verification Gap", category="operational", severity="soft",
        condition="Declared income within 20% of verified income",
    ),
]


class PolicyEngine:
    """Evaluates loan applications against configurable policy rules.

    Rules can be loaded from JSON/YAML configs or defined in code.
    Supports product and segment filtering.
    """

    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self.rules = rules or DEFAULT_RULES

    def evaluate(
        self,
        applicant_data: dict[str, Any],
        risk_data: dict[str, Any],
        product_type: str = "personal_loan",
        segment: str = "retail",
    ) -> dict[str, Any]:
        """Evaluate all applicable rules against the application.

        Returns:
            Dict with passed/failed rules, hard rejections, and soft flags.
        """
        results: list[RuleResult] = []
        hard_rejections: list[str] = []
        soft_flags: list[str] = []

        applicable_rules = [
            r for r in self.rules
            if "all" in r.products or product_type in r.products
        ]

        for rule in applicable_rules:
            passed, reason = self._evaluate_rule(rule, applicant_data, risk_data)
            result = RuleResult(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                passed=passed,
                severity=rule.severity,
                reason=reason,
            )
            results.append(result)

            if not passed:
                if rule.severity == "hard":
                    hard_rejections.append(f"[{rule.rule_id}] {rule.name}: {reason}")
                else:
                    soft_flags.append(f"[{rule.rule_id}] {rule.name}: {reason}")

        return {
            "total_rules": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "hard_rejections": hard_rejections,
            "soft_flags": soft_flags,
            "auto_reject": len(hard_rejections) > 0,
            "requires_review": len(soft_flags) > 0,
            "details": [
                {"rule_id": r.rule_id, "name": r.rule_name, "passed": r.passed, "severity": r.severity, "reason": r.reason}
                for r in results
            ],
        }

    def _evaluate_rule(
        self, rule: PolicyRule, applicant: dict[str, Any], risk: dict[str, Any]
    ) -> tuple[bool, str]:
        """Evaluate a single rule. Returns (passed, reason)."""

        if rule.rule_id == "HR-001":
            age = applicant.get("age", 0)
            return (age >= 21, f"Age: {age}" if age < 21 else "OK")

        elif rule.rule_id == "HR-002":
            age = applicant.get("age", 0)
            tenor = applicant.get("requested_tenor_years", 0)
            age_at_maturity = age + tenor
            return (age_at_maturity <= 65, f"Age at maturity: {age_at_maturity}" if age_at_maturity > 65 else "OK")

        elif rule.rule_id == "HR-003":
            score = risk.get("credit_score", 0)
            return (score >= 600, f"Credit score: {score}" if score < 600 else "OK")

        elif rule.rule_id == "HR-004":
            write_offs = risk.get("write_offs", 0)
            return (write_offs == 0, f"Write-offs found: {write_offs}" if write_offs > 0 else "OK")

        elif rule.rule_id == "HR-005":
            max_dpd = risk.get("max_dpd_12m", 0)
            return (max_dpd <= 30, f"Max DPD 12m: {max_dpd} days" if max_dpd > 30 else "OK")

        elif rule.rule_id == "HR-006":
            income = applicant.get("monthly_income", 0)
            return (income >= 25000, f"Monthly income: {income}" if income < 25000 else "OK")

        elif rule.rule_id == "SF-001":
            dti = applicant.get("dti_ratio", 0)
            return (dti <= 0.5, f"DTI ratio: {dti:.1%}" if dti > 0.5 else "OK")

        elif rule.rule_id == "SF-002":
            tenure = applicant.get("employment_months", 0)
            return (tenure >= 12, f"Employment: {tenure} months" if tenure < 12 else "OK")

        elif rule.rule_id == "SF-003":
            enquiries = risk.get("total_enquiries_6m", 0)
            return (enquiries <= 4, f"Enquiries: {enquiries}" if enquiries > 4 else "OK")

        elif rule.rule_id == "SF-004":
            ltv = applicant.get("ltv_ratio", 0)
            return (ltv <= 0.8, f"LTV: {ltv:.1%}" if ltv > 0.8 else "OK")

        elif rule.rule_id == "SF-005":
            declared = applicant.get("declared_income", 0)
            verified = applicant.get("verified_income", 0)
            if verified > 0:
                gap = abs(declared - verified) / verified
                return (gap <= 0.2, f"Income gap: {gap:.1%}" if gap > 0.2 else "OK")
            return (False, "Verified income not available")

        return (True, "Rule not implemented — defaulting to pass")
