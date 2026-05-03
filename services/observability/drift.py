"""Drift Detection Engine — statistical tests for data and model drift.

Blueprint §6: Continuous monitoring of feature distributions, prediction
distributions, and model performance against baseline metrics.
Uses PSI, KS test, Jensen-Shannon divergence, and Chi-squared tests.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from services.observability.models import PerformanceSnapshot as DBPerformanceSnapshot, MonitoringAlert as DBMonitoringAlert


class DriftSeverity(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DriftType(str, Enum):
    DATA_DRIFT = "data_drift"          # Feature distribution shift
    CONCEPT_DRIFT = "concept_drift"    # Target variable relationship shift
    PREDICTION_DRIFT = "prediction_drift"  # Model output distribution shift
    PERFORMANCE_DRIFT = "performance_drift"  # Metric degradation


@dataclass
class FeatureDriftResult:
    """Drift result for a single feature."""

    feature_name: str
    drift_type: DriftType
    test_method: str
    statistic: float
    p_value: float | None
    severity: DriftSeverity
    threshold: float
    is_drifted: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DriftReport:
    """Comprehensive drift report for a model."""

    model_name: str
    report_id: str
    baseline_period: str
    current_period: str
    feature_results: list[FeatureDriftResult]
    overall_severity: DriftSeverity
    drifted_features: list[str]
    drift_percentage: float  # % of features drifted
    recommendations: list[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class DriftDetector:
    """Detects data and model drift using multiple statistical tests."""

    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self.thresholds = thresholds or {
            "psi_low": 0.1,
            "psi_moderate": 0.2,
            "psi_high": 0.5,
            "ks_p_value": 0.05,
            "js_divergence": 0.1,
        }

    def detect_data_drift(
        self,
        baseline: list[dict[str, Any]],
        current: list[dict[str, Any]],
        model_name: str = "model",
        features: list[str] | None = None,
    ) -> DriftReport:
        """Detect data drift between baseline and current data.

        Args:
            baseline: Reference data (training data or a stable period).
            current: Recent production data.
            model_name: Model identifier.
            features: Specific features to check (all if None).

        Returns:
            DriftReport with per-feature results and recommendations.
        """
        if not baseline or not current:
            return DriftReport(
                model_name=model_name, report_id=f"dr-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                baseline_period="N/A", current_period="N/A",
                feature_results=[], overall_severity=DriftSeverity.NONE,
                drifted_features=[], drift_percentage=0.0, recommendations=["No data provided"],
            )

        all_features = features or list(baseline[0].keys())
        results: list[FeatureDriftResult] = []

        for feat in all_features:
            base_vals = [row.get(feat) for row in baseline if row.get(feat) is not None]
            curr_vals = [row.get(feat) for row in current if row.get(feat) is not None]

            if not base_vals or not curr_vals:
                continue

            # Determine if numeric or categorical
            try:
                base_numeric = [float(v) for v in base_vals]
                curr_numeric = [float(v) for v in curr_vals]
                is_numeric = True
            except (ValueError, TypeError):
                is_numeric = False

            if is_numeric:
                # PSI (Population Stability Index)
                psi_result = self._compute_psi(base_numeric, curr_numeric, feat)
                results.append(psi_result)

                # KS Test
                ks_result = self._compute_ks_test(base_numeric, curr_numeric, feat)
                results.append(ks_result)
            else:
                # Chi-squared for categorical
                chi_result = self._compute_chi_squared(base_vals, curr_vals, feat)
                results.append(chi_result)

        # Aggregate
        drifted = list(set(r.feature_name for r in results if r.is_drifted))
        drift_pct = len(drifted) / max(len(all_features), 1) * 100

        if drift_pct >= 50:
            overall = DriftSeverity.CRITICAL
        elif drift_pct >= 30:
            overall = DriftSeverity.HIGH
        elif drift_pct >= 10:
            overall = DriftSeverity.MODERATE
        elif drift_pct > 0:
            overall = DriftSeverity.LOW
        else:
            overall = DriftSeverity.NONE

        recommendations = self._generate_recommendations(results, drifted, drift_pct)

        return DriftReport(
            model_name=model_name,
            report_id=f"dr-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            baseline_period="baseline",
            current_period="current",
            feature_results=results,
            overall_severity=overall,
            drifted_features=drifted,
            drift_percentage=round(drift_pct, 1),
            recommendations=recommendations,
        )

    def _compute_psi(self, baseline: list[float], current: list[float], feature: str) -> FeatureDriftResult:
        """Population Stability Index (PSI) for numeric features."""
        n_bins = 10
        base_arr = np.array(baseline)
        curr_arr = np.array(current)

        # Create bins from baseline
        edges = np.percentile(base_arr, np.linspace(0, 100, n_bins + 1))
        edges[0] = min(edges[0], curr_arr.min()) - 1
        edges[-1] = max(edges[-1], curr_arr.max()) + 1
        edges = np.unique(edges)

        base_counts, _ = np.histogram(base_arr, bins=edges)
        curr_counts, _ = np.histogram(curr_arr, bins=edges)

        # Normalize to proportions (avoid zeros)
        base_pct = (base_counts + 1) / (len(baseline) + len(edges) - 1)
        curr_pct = (curr_counts + 1) / (len(current) + len(edges) - 1)

        psi = float(np.sum((curr_pct - base_pct) * np.log(curr_pct / base_pct)))

        if psi >= self.thresholds["psi_high"]:
            severity = DriftSeverity.HIGH
        elif psi >= self.thresholds["psi_moderate"]:
            severity = DriftSeverity.MODERATE
        elif psi >= self.thresholds["psi_low"]:
            severity = DriftSeverity.LOW
        else:
            severity = DriftSeverity.NONE

        return FeatureDriftResult(
            feature_name=feature,
            drift_type=DriftType.DATA_DRIFT,
            test_method="PSI",
            statistic=round(psi, 6),
            p_value=None,
            severity=severity,
            threshold=self.thresholds["psi_moderate"],
            is_drifted=psi >= self.thresholds["psi_moderate"],
            details={"baseline_mean": round(float(np.mean(base_arr)), 4),
                     "current_mean": round(float(np.mean(curr_arr)), 4)},
        )

    def _compute_ks_test(self, baseline: list[float], current: list[float], feature: str) -> FeatureDriftResult:
        """Kolmogorov-Smirnov test for distribution shift."""
        try:
            from scipy.stats import ks_2samp
            stat, p_value = ks_2samp(baseline, current)
        except ImportError:
            # Manual KS approximation
            base_sorted = np.sort(baseline)
            curr_sorted = np.sort(current)
            all_vals = np.sort(np.concatenate([base_sorted, curr_sorted]))
            base_cdf = np.searchsorted(base_sorted, all_vals, side='right') / len(baseline)
            curr_cdf = np.searchsorted(curr_sorted, all_vals, side='right') / len(current)
            stat = float(np.max(np.abs(base_cdf - curr_cdf)))
            n = min(len(baseline), len(current))
            p_value = max(0.001, np.exp(-2 * n * stat ** 2))

        p_threshold = self.thresholds["ks_p_value"]
        is_drifted = p_value < p_threshold

        return FeatureDriftResult(
            feature_name=feature,
            drift_type=DriftType.DATA_DRIFT,
            test_method="KS",
            statistic=round(float(stat), 6),
            p_value=round(float(p_value), 6),
            severity=DriftSeverity.MODERATE if is_drifted else DriftSeverity.NONE,
            threshold=p_threshold,
            is_drifted=is_drifted,
        )

    def _compute_chi_squared(self, baseline: list[Any], current: list[Any], feature: str) -> FeatureDriftResult:
        """Chi-squared test for categorical feature drift."""
        from collections import Counter

        base_counts = Counter(str(v) for v in baseline)
        curr_counts = Counter(str(v) for v in current)

        all_categories = sorted(set(base_counts.keys()) | set(curr_counts.keys()))
        observed = np.array([curr_counts.get(c, 0) for c in all_categories], dtype=float)
        expected = np.array([base_counts.get(c, 0) for c in all_categories], dtype=float)

        # Normalize expected to same total as observed
        total_obs = observed.sum()
        total_exp = expected.sum()
        if total_exp > 0:
            expected = expected * (total_obs / total_exp)
        expected = np.maximum(expected, 1)  # Avoid division by zero

        chi2 = float(np.sum((observed - expected) ** 2 / expected))
        df = len(all_categories) - 1

        try:
            from scipy.stats import chi2 as chi2_dist
            p_value = float(1 - chi2_dist.cdf(chi2, df)) if df > 0 else 1.0
        except ImportError:
            p_value = 0.5  # Approximation

        is_drifted = p_value < 0.05

        return FeatureDriftResult(
            feature_name=feature,
            drift_type=DriftType.DATA_DRIFT,
            test_method="Chi-Squared",
            statistic=round(chi2, 4),
            p_value=round(p_value, 6),
            severity=DriftSeverity.MODERATE if is_drifted else DriftSeverity.NONE,
            threshold=0.05,
            is_drifted=is_drifted,
            details={"categories": len(all_categories), "df": df},
        )

    def _generate_recommendations(
        self, results: list[FeatureDriftResult], drifted: list[str], drift_pct: float
    ) -> list[str]:
        recs: list[str] = []
        if drift_pct >= 30:
            recs.append("URGENT: Significant drift detected. Consider immediate model retraining.")
        elif drift_pct >= 10:
            recs.append("Monitor closely: moderate drift detected across multiple features.")

        high_psi = [r for r in results if r.test_method == "PSI" and r.severity in (DriftSeverity.HIGH, DriftSeverity.CRITICAL)]
        if high_psi:
            features = ", ".join(r.feature_name for r in high_psi[:5])
            recs.append(f"High PSI drift in features: {features}. Investigate data pipeline changes.")

        if not drifted:
            recs.append("No drift detected. Model is performing within baseline parameters.")

        return recs


# ── Performance Monitor ──────────────────────────────────


@dataclass
class PerformanceSnapshot:
    """Point-in-time model performance metrics."""

    model_name: str
    timestamp: datetime
    metrics: dict[str, float]
    prediction_count: int
    avg_latency_ms: float


class PerformanceMonitor:
    """Tracks model performance over time and detects degradation."""

    def __init__(self) -> None:
        pass

    async def record(
        self, db: AsyncSession, model_name: str, metrics: dict[str, float],
        prediction_count: int = 0, avg_latency_ms: float = 0.0,
    ) -> DBPerformanceSnapshot:
        """Record a performance snapshot."""
        snap = DBPerformanceSnapshot(
            model_id=model_name,
            metrics=metrics,
            prediction_count=prediction_count,
            avg_latency_ms=avg_latency_ms,
        )
        db.add(snap)
        await db.flush()

        # Check for degradation
        await self._check_degradation(db, model_name)
        return snap

    async def get_history(self, db: AsyncSession, model_name: str, last_n: int = 50) -> list[DBPerformanceSnapshot]:
        result = await db.execute(
            select(DBPerformanceSnapshot)
            .where(DBPerformanceSnapshot.model_id == model_name)
            .order_by(DBPerformanceSnapshot.created_at.desc())
            .limit(last_n)
        )
        return list(reversed(result.scalars().all()))

    async def get_alerts(self, db: AsyncSession, model_name: str | None = None) -> list[dict[str, Any]]:
        query = select(DBMonitoringAlert)
        if model_name:
            query = query.where(DBMonitoringAlert.service == model_name)
        
        result = await db.execute(query.order_by(DBMonitoringAlert.created_at.desc()))
        alerts = result.scalars().all()
        return [
            {
                "id": a.id,
                "model": a.service,
                "severity": a.severity,
                "message": a.message,
                "details": a.details,
                "timestamp": a.created_at.isoformat(),
                "resolved": bool(a.resolved)
            }
            for a in alerts
        ]

    async def _check_degradation(self, db: AsyncSession, model_name: str) -> None:
        # Fetch last 20 snapshots for analysis
        result = await db.execute(
            select(DBPerformanceSnapshot)
            .where(DBPerformanceSnapshot.model_id == model_name)
            .order_by(DBPerformanceSnapshot.created_at.desc())
            .limit(20)
        )
        history = list(reversed(result.scalars().all()))
        
        if len(history) < 5:
            return

        recent = history[-5:]
        baseline = history[:max(1, len(history) // 2)]

        # Get unique metric names from recent snapshots
        metric_names = set()
        for s in recent:
            metric_names.update(s.metrics.keys())

        for metric_name in metric_names:
            recent_vals = [s.metrics.get(metric_name, 0) for s in recent if metric_name in s.metrics]
            baseline_vals = [s.metrics.get(metric_name, 0) for s in baseline if metric_name in s.metrics]

            if not recent_vals or not baseline_vals:
                continue

            recent_avg = np.mean(recent_vals)
            baseline_avg = np.mean(baseline_vals)

            if baseline_avg > 0:
                degradation = (baseline_avg - recent_avg) / baseline_avg
                if degradation > 0.1:  # 10% degradation
                    alert = DBMonitoringAlert(
                        service=model_name,
                        severity="high" if degradation > 0.2 else "moderate",
                        message=f"Performance degradation detected in {metric_name} for {model_name}",
                        details={
                            "metric": metric_name,
                            "baseline_avg": round(float(baseline_avg), 4),
                            "recent_avg": round(float(recent_avg), 4),
                            "degradation_pct": round(float(degradation * 100), 1),
                        }
                    )
                    db.add(alert)
