"""Fairness Engine — bias detection and assessment for ML models.

Blueprint §3.4: Evaluates models against protected attributes using
standard fairness metrics (demographic parity, equal opportunity,
equalized odds, predictive parity) for regulatory compliance.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class FairnessMetric:
    """A single fairness metric result."""

    name: str
    value: float
    threshold: float
    is_fair: bool
    description: str


@dataclass
class GroupMetrics:
    """Metrics for a specific group (e.g., male, female)."""

    group_name: str
    group_size: int
    positive_rate: float  # Selection rate / positive prediction rate
    true_positive_rate: float  # TPR / Recall
    false_positive_rate: float
    precision: float
    accuracy: float


@dataclass
class FairnessReport:
    """Comprehensive fairness assessment report."""

    model_name: str
    protected_attribute: str
    groups: list[GroupMetrics]
    metrics: list[FairnessMetric]
    overall_is_fair: bool
    recommendations: list[str] = field(default_factory=list)


class FairnessEngine:
    """Evaluates model fairness across protected groups.

    Supported metrics:
    - Demographic Parity Difference/Ratio
    - Equal Opportunity Difference
    - Equalized Odds Difference
    - Predictive Parity Difference
    """

    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self.thresholds = thresholds or {
            "demographic_parity_difference": 0.1,
            "demographic_parity_ratio": 0.8,
            "equal_opportunity_difference": 0.1,
            "equalized_odds_difference": 0.1,
            "predictive_parity_difference": 0.1,
        }

    def assess(
        self,
        y_true: list[Any],
        y_pred: list[Any],
        protected_attr: list[Any],
        model_name: str = "model",
        attribute_name: str = "protected",
    ) -> FairnessReport:
        """Run full fairness assessment.

        Args:
            y_true: Ground truth labels (0/1).
            y_pred: Model predictions (0/1).
            protected_attr: Protected attribute values per instance.
            model_name: Name for the report.
            attribute_name: Name of the protected attribute.

        Returns:
            FairnessReport with group metrics, fairness metrics, and recommendations.
        """
        y_true_arr = np.array(y_true, dtype=int)
        y_pred_arr = np.array(y_pred, dtype=int)
        groups_arr = np.array(protected_attr)

        unique_groups = sorted(set(groups_arr.tolist()))
        group_metrics: list[GroupMetrics] = []

        for group in unique_groups:
            mask = groups_arr == group
            g_true = y_true_arr[mask]
            g_pred = y_pred_arr[mask]
            group_size = int(mask.sum())

            positive_rate = float(g_pred.mean()) if group_size > 0 else 0.0

            # TPR = TP / (TP + FN)
            positives = g_true == 1
            tp = int(((g_pred == 1) & positives).sum())
            fn = int(((g_pred == 0) & positives).sum())
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0

            # FPR = FP / (FP + TN)
            negatives = g_true == 0
            fp = int(((g_pred == 1) & negatives).sum())
            tn = int(((g_pred == 0) & negatives).sum())
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

            # Precision
            pred_pos = int((g_pred == 1).sum())
            precision = tp / pred_pos if pred_pos > 0 else 0.0

            # Accuracy
            accuracy = float((g_true == g_pred).mean()) if group_size > 0 else 0.0

            group_metrics.append(GroupMetrics(
                group_name=str(group),
                group_size=group_size,
                positive_rate=round(positive_rate, 4),
                true_positive_rate=round(tpr, 4),
                false_positive_rate=round(fpr, 4),
                precision=round(precision, 4),
                accuracy=round(accuracy, 4),
            ))

        # Compute fairness metrics
        fairness_metrics: list[FairnessMetric] = []
        recommendations: list[str] = []

        if len(group_metrics) >= 2:
            rates = [g.positive_rate for g in group_metrics]
            tprs = [g.true_positive_rate for g in group_metrics]
            fprs = [g.false_positive_rate for g in group_metrics]
            precisions = [g.precision for g in group_metrics]

            # 1. Demographic Parity Difference
            dpd = max(rates) - min(rates)
            dpd_threshold = self.thresholds["demographic_parity_difference"]
            fairness_metrics.append(FairnessMetric(
                name="Demographic Parity Difference",
                value=round(dpd, 4),
                threshold=dpd_threshold,
                is_fair=dpd <= dpd_threshold,
                description="Difference in positive prediction rates across groups. Lower is fairer.",
            ))
            if dpd > dpd_threshold:
                high_group = group_metrics[rates.index(max(rates))].group_name
                low_group = group_metrics[rates.index(min(rates))].group_name
                recommendations.append(
                    f"Selection rate disparity: {high_group} ({max(rates):.1%}) vs {low_group} ({min(rates):.1%}). "
                    f"Consider rebalancing training data or adjusting decision threshold per group."
                )

            # 2. Demographic Parity Ratio
            dpr = min(rates) / max(rates) if max(rates) > 0 else 1.0
            dpr_threshold = self.thresholds["demographic_parity_ratio"]
            fairness_metrics.append(FairnessMetric(
                name="Demographic Parity Ratio",
                value=round(dpr, 4),
                threshold=dpr_threshold,
                is_fair=dpr >= dpr_threshold,
                description="Ratio of positive prediction rates (min/max). The 4/5ths rule uses 0.8.",
            ))

            # 3. Equal Opportunity Difference
            eod = max(tprs) - min(tprs)
            eod_threshold = self.thresholds["equal_opportunity_difference"]
            fairness_metrics.append(FairnessMetric(
                name="Equal Opportunity Difference",
                value=round(eod, 4),
                threshold=eod_threshold,
                is_fair=eod <= eod_threshold,
                description="Difference in true positive rates across groups.",
            ))
            if eod > eod_threshold:
                recommendations.append(
                    "Equal opportunity violation: model has different recall rates for qualified "
                    "applicants across groups. Review feature selection for proxy bias."
                )

            # 4. Equalized Odds Difference
            eq_odds = max(max(tprs) - min(tprs), max(fprs) - min(fprs))
            eq_threshold = self.thresholds["equalized_odds_difference"]
            fairness_metrics.append(FairnessMetric(
                name="Equalized Odds Difference",
                value=round(eq_odds, 4),
                threshold=eq_threshold,
                is_fair=eq_odds <= eq_threshold,
                description="Max of TPR and FPR differences across groups.",
            ))

            # 5. Predictive Parity Difference
            ppd = max(precisions) - min(precisions)
            pp_threshold = self.thresholds["predictive_parity_difference"]
            fairness_metrics.append(FairnessMetric(
                name="Predictive Parity Difference",
                value=round(ppd, 4),
                threshold=pp_threshold,
                is_fair=ppd <= pp_threshold,
                description="Difference in precision across groups.",
            ))

        overall_fair = all(m.is_fair for m in fairness_metrics)

        if overall_fair:
            recommendations.append("All fairness metrics are within acceptable thresholds.")
        else:
            failed = [m.name for m in fairness_metrics if not m.is_fair]
            recommendations.insert(0, f"ATTENTION: {len(failed)} fairness metric(s) failed: {', '.join(failed)}.")

        return FairnessReport(
            model_name=model_name,
            protected_attribute=attribute_name,
            groups=group_metrics,
            metrics=fairness_metrics,
            overall_is_fair=overall_fair,
            recommendations=recommendations,
        )
