"""Data Profiling Service — statistical analysis and quality assessment.

Generates column-level statistics, correlation matrices, and data quality alerts.
Blueprint §3.1: profiling is the first step before any ML pipeline.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ColumnProfile:
    """Statistical profile for a single column."""

    name: str
    dtype: str
    count: int
    missing_count: int
    missing_pct: float
    unique_count: int
    unique_pct: float

    # Numeric stats (None for non-numeric)
    mean: float | None = None
    std: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    median: float | None = None
    q25: float | None = None
    q75: float | None = None
    skewness: float | None = None
    kurtosis: float | None = None

    # Categorical stats
    top_values: list[tuple[str, int]] | None = None

    # Quality alerts
    alerts: list[str] = field(default_factory=list)


@dataclass
class DatasetProfile:
    """Full profiling report for a dataset."""

    dataset_name: str
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    correlations: dict[str, dict[str, float]] | None = None
    quality_score: float = 0.0  # 0-100
    alerts: list[str] = field(default_factory=list)


class ProfilingService:
    """Generates statistical profiles for datasets.

    Computes per-column statistics, correlation matrices, and
    quality alerts following the Blueprint §3.1 spec.
    """

    def __init__(self, alert_thresholds: dict[str, float] | None = None) -> None:
        self.thresholds = alert_thresholds or {
            "missing_pct_warn": 5.0,
            "missing_pct_critical": 30.0,
            "high_correlation": 0.95,
            "low_unique_ratio": 0.01,
            "high_skewness": 2.0,
        }

    def profile_dataset(self, data: list[dict[str, Any]], dataset_name: str = "untitled") -> DatasetProfile:
        """Profile an entire dataset.

        Args:
            data: List of row dicts (from connector extraction).
            dataset_name: Name for the profile report.

        Returns:
            DatasetProfile with per-column stats and quality alerts.
        """
        if not data:
            return DatasetProfile(dataset_name=dataset_name, row_count=0, column_count=0, columns=[])

        row_count = len(data)
        columns = list(data[0].keys())
        column_profiles: list[ColumnProfile] = []
        dataset_alerts: list[str] = []

        for col in columns:
            values = [row.get(col) for row in data]
            profile = self._profile_column(col, values, row_count)
            column_profiles.append(profile)

        # Compute correlations for numeric columns
        numeric_cols = [p for p in column_profiles if p.dtype == "numeric"]
        correlations = self._compute_correlations(data, numeric_cols) if len(numeric_cols) >= 2 else None

        # Check for high correlations
        if correlations:
            threshold = self.thresholds["high_correlation"]
            for c1 in correlations:
                for c2, corr_val in correlations[c1].items():
                    if c1 < c2 and abs(corr_val) >= threshold:
                        alert = f"High correlation ({corr_val:.3f}) between '{c1}' and '{c2}'"
                        dataset_alerts.append(alert)

        # Compute quality score
        quality_score = self._compute_quality_score(column_profiles, row_count)

        return DatasetProfile(
            dataset_name=dataset_name,
            row_count=row_count,
            column_count=len(columns),
            columns=column_profiles,
            correlations=correlations,
            quality_score=quality_score,
            alerts=dataset_alerts,
        )

    def _profile_column(self, name: str, values: list[Any], total: int) -> ColumnProfile:
        """Compute statistics for a single column."""
        non_null = [v for v in values if v is not None and str(v).strip() != ""]
        missing_count = total - len(non_null)
        missing_pct = (missing_count / total * 100) if total > 0 else 0
        unique_vals = set(str(v) for v in non_null)
        unique_count = len(unique_vals)
        unique_pct = (unique_count / len(non_null) * 100) if non_null else 0

        alerts: list[str] = []

        # Check if numeric
        numeric_values: list[float] = []
        for v in non_null:
            try:
                numeric_values.append(float(v))
            except (ValueError, TypeError):
                pass

        is_numeric = len(numeric_values) > len(non_null) * 0.8  # 80%+ parseable as numeric

        profile = ColumnProfile(
            name=name,
            dtype="numeric" if is_numeric else "categorical",
            count=total,
            missing_count=missing_count,
            missing_pct=round(missing_pct, 2),
            unique_count=unique_count,
            unique_pct=round(unique_pct, 2),
        )

        # Alerts
        if missing_pct >= self.thresholds["missing_pct_critical"]:
            alerts.append(f"CRITICAL: {missing_pct:.1f}% missing values")
        elif missing_pct >= self.thresholds["missing_pct_warn"]:
            alerts.append(f"WARNING: {missing_pct:.1f}% missing values")

        if unique_pct < self.thresholds["low_unique_ratio"] and len(non_null) > 100:
            alerts.append(f"Low cardinality: {unique_count} unique values ({unique_pct:.2f}%)")

        if is_numeric and numeric_values:
            arr = np.array(numeric_values)
            profile.mean = round(float(np.mean(arr)), 4)
            profile.std = round(float(np.std(arr)), 4)
            profile.min_val = round(float(np.min(arr)), 4)
            profile.max_val = round(float(np.max(arr)), 4)
            profile.median = round(float(np.median(arr)), 4)
            profile.q25 = round(float(np.percentile(arr, 25)), 4)
            profile.q75 = round(float(np.percentile(arr, 75)), 4)

            if len(arr) > 3:
                from scipy import stats as sp_stats

                profile.skewness = round(float(sp_stats.skew(arr)), 4)
                profile.kurtosis = round(float(sp_stats.kurtosis(arr)), 4)

                if abs(profile.skewness) > self.thresholds["high_skewness"]:
                    alerts.append(f"High skewness: {profile.skewness:.2f}")
        else:
            # Top categorical values
            from collections import Counter

            counter = Counter(str(v) for v in non_null)
            profile.top_values = counter.most_common(10)

        profile.alerts = alerts
        return profile

    def _compute_correlations(
        self, data: list[dict[str, Any]], numeric_cols: list[ColumnProfile]
    ) -> dict[str, dict[str, float]]:
        """Compute Pearson correlations between numeric columns."""
        col_names = [p.name for p in numeric_cols]
        matrix: dict[str, dict[str, float]] = {}

        # Build numeric arrays
        arrays: dict[str, list[float]] = {}
        for col in col_names:
            arr: list[float] = []
            for row in data:
                try:
                    arr.append(float(row.get(col, 0) or 0))
                except (ValueError, TypeError):
                    arr.append(0.0)
            arrays[col] = arr

        for c1 in col_names:
            matrix[c1] = {}
            for c2 in col_names:
                if c1 == c2:
                    matrix[c1][c2] = 1.0
                else:
                    a1 = np.array(arrays[c1])
                    a2 = np.array(arrays[c2])
                    if np.std(a1) > 0 and np.std(a2) > 0:
                        corr = float(np.corrcoef(a1, a2)[0, 1])
                        matrix[c1][c2] = round(corr, 4)
                    else:
                        matrix[c1][c2] = 0.0

        return matrix

    def _compute_quality_score(self, profiles: list[ColumnProfile], row_count: int) -> float:
        """Compute an overall data quality score (0-100)."""
        if not profiles:
            return 0.0

        scores: list[float] = []
        for p in profiles:
            col_score = 100.0
            # Penalize missing values
            col_score -= min(p.missing_pct, 50.0)
            # Penalize if all values identical
            if p.unique_count <= 1 and p.count > 10:
                col_score -= 30.0
            # Penalize extreme skewness
            if p.skewness and abs(p.skewness) > 3:
                col_score -= 10.0
            scores.append(max(col_score, 0.0))

        return round(sum(scores) / len(scores), 1)
