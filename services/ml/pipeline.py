"""7-Step Data Cleaning Pipeline — modular transformers for ML preprocessing.

Blueprint §3.2: The cleaning pipeline follows these ordered steps:
1. Unique ratio filter (remove columns with too many unique values, e.g. IDs)
2. Low-information removal (near-zero variance columns)
3. Missing value imputation (mean/median/mode or drop)
4. Outlier treatment (IQR, z-score, or clip)
5. Categorical encoding (label, one-hot, target)
6. Numeric transformations & scaling (standard, minmax, log)
7. Near-zero variance removal (post-encoding cleanup)

Each step is a standalone transformer that can be configured and chained.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class StepResult:
    """Result of a single cleaning step."""

    step_name: str
    columns_before: int
    columns_after: int
    rows_before: int
    rows_after: int
    columns_removed: list[str] = field(default_factory=list)
    columns_modified: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class BaseTransformer(ABC):
    """Abstract transformer step in the cleaning pipeline."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def fit_transform(self, data: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], StepResult]:
        ...


class UniqueRatioFilter(BaseTransformer):
    """Step 1: Remove columns where unique ratio exceeds threshold (likely IDs)."""

    @property
    def name(self) -> str:
        return "unique_ratio_filter"

    def fit_transform(self, data: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], StepResult]:
        threshold = config.get("max_unique_ratio", 0.95)
        if not data:
            return data, StepResult(self.name, 0, 0, 0, 0)

        cols = list(data[0].keys())
        cols_to_remove: list[str] = []

        for col in cols:
            values = [row.get(col) for row in data if row.get(col) is not None]
            if values:
                unique_ratio = len(set(values)) / len(values)
                if unique_ratio >= threshold and len(values) > 20:
                    cols_to_remove.append(col)

        result_data = [{k: v for k, v in row.items() if k not in cols_to_remove} for row in data]
        remaining = list(result_data[0].keys()) if result_data else []

        return result_data, StepResult(
            self.name, len(cols), len(remaining), len(data), len(result_data),
            columns_removed=cols_to_remove,
        )


class LowInfoRemoval(BaseTransformer):
    """Step 2: Remove near-zero variance columns (pre-encoding)."""

    @property
    def name(self) -> str:
        return "low_info_removal"

    def fit_transform(self, data: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], StepResult]:
        min_unique = config.get("min_unique_values", 2)
        if not data:
            return data, StepResult(self.name, 0, 0, 0, 0)

        cols = list(data[0].keys())
        cols_to_remove: list[str] = []

        for col in cols:
            values = set(str(row.get(col, "")) for row in data)
            if len(values) < min_unique:
                cols_to_remove.append(col)

        result_data = [{k: v for k, v in row.items() if k not in cols_to_remove} for row in data]
        remaining = list(result_data[0].keys()) if result_data else []

        return result_data, StepResult(
            self.name, len(cols), len(remaining), len(data), len(result_data),
            columns_removed=cols_to_remove,
        )


class MissingValueImputer(BaseTransformer):
    """Step 3: Impute or drop missing values."""

    @property
    def name(self) -> str:
        return "missing_value_imputer"

    def fit_transform(self, data: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], StepResult]:
        strategy = config.get("strategy", "median")  # mean, median, mode, drop_rows, drop_cols
        drop_threshold = config.get("drop_threshold", 0.5)  # Drop cols with >50% missing

        if not data:
            return data, StepResult(self.name, 0, 0, 0, 0)

        cols = list(data[0].keys())
        cols_to_remove: list[str] = []
        modified: list[str] = []

        # Phase 1: drop columns with too many missing values
        for col in cols:
            missing = sum(1 for row in data if row.get(col) is None or str(row.get(col, "")).strip() == "")
            if missing / len(data) > drop_threshold:
                cols_to_remove.append(col)

        result_data = [{k: v for k, v in row.items() if k not in cols_to_remove} for row in data]
        remaining_cols = [c for c in cols if c not in cols_to_remove]

        # Phase 2: impute remaining missing values
        if strategy == "drop_rows":
            result_data = [
                row for row in result_data
                if all(row.get(c) is not None and str(row.get(c, "")).strip() != "" for c in remaining_cols)
            ]
        else:
            for col in remaining_cols:
                values = [row.get(col) for row in result_data if row.get(col) is not None and str(row.get(col, "")).strip() != ""]
                if not values:
                    continue

                # Determine fill value
                try:
                    numeric = [float(v) for v in values]
                    if strategy == "mean":
                        fill = np.mean(numeric)
                    elif strategy == "median":
                        fill = np.median(numeric)
                    else:
                        from collections import Counter
                        fill = Counter(values).most_common(1)[0][0]
                except (ValueError, TypeError):
                    from collections import Counter
                    fill = Counter(values).most_common(1)[0][0]

                # Apply fill
                filled = False
                for row in result_data:
                    if row.get(col) is None or str(row.get(col, "")).strip() == "":
                        row[col] = fill
                        filled = True
                if filled:
                    modified.append(col)

        return result_data, StepResult(
            self.name, len(cols), len(remaining_cols), len(data), len(result_data),
            columns_removed=cols_to_remove, columns_modified=modified,
        )


class OutlierTreatment(BaseTransformer):
    """Step 4: Detect and treat outliers using IQR or z-score."""

    @property
    def name(self) -> str:
        return "outlier_treatment"

    def fit_transform(self, data: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], StepResult]:
        method = config.get("method", "iqr")  # iqr, zscore, clip
        iqr_factor = config.get("iqr_factor", 1.5)
        zscore_threshold = config.get("zscore_threshold", 3.0)

        if not data:
            return data, StepResult(self.name, 0, 0, 0, 0)

        cols = list(data[0].keys())
        modified: list[str] = []

        for col in cols:
            try:
                values = [float(row[col]) for row in data if row.get(col) is not None]
            except (ValueError, TypeError):
                continue

            if len(values) < 10:
                continue

            arr = np.array(values)

            if method == "iqr":
                q1, q3 = np.percentile(arr, [25, 75])
                iqr = q3 - q1
                lower = q1 - iqr_factor * iqr
                upper = q3 + iqr_factor * iqr
            else:  # zscore
                mean, std = np.mean(arr), np.std(arr)
                lower = mean - zscore_threshold * std
                upper = mean + zscore_threshold * std

            clipped = False
            for row in data:
                try:
                    val = float(row[col])
                    if val < lower:
                        row[col] = float(lower)
                        clipped = True
                    elif val > upper:
                        row[col] = float(upper)
                        clipped = True
                except (ValueError, TypeError, KeyError):
                    pass

            if clipped:
                modified.append(col)

        return data, StepResult(
            self.name, len(cols), len(cols), len(data), len(data),
            columns_modified=modified,
        )


class CategoricalEncoder(BaseTransformer):
    """Step 5: Encode categorical columns."""

    @property
    def name(self) -> str:
        return "categorical_encoder"

    def fit_transform(self, data: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], StepResult]:
        method = config.get("method", "label")  # label, onehot
        max_categories = config.get("max_categories", 20)

        if not data:
            return data, StepResult(self.name, 0, 0, 0, 0)

        cols = list(data[0].keys())
        cat_cols: list[str] = []

        for col in cols:
            values = [row.get(col) for row in data if row.get(col) is not None]
            if not values:
                continue
            try:
                [float(v) for v in values[:50]]
            except (ValueError, TypeError):
                unique = set(str(v) for v in values)
                if len(unique) <= max_categories:
                    cat_cols.append(col)

        if method == "label":
            for col in cat_cols:
                unique_vals = sorted(set(str(row.get(col, "")) for row in data))
                label_map = {v: i for i, v in enumerate(unique_vals)}
                for row in data:
                    row[col] = label_map.get(str(row.get(col, "")), -1)

        elif method == "onehot":
            new_data: list[dict[str, Any]] = []
            for row in data:
                new_row = {k: v for k, v in row.items() if k not in cat_cols}
                for col in cat_cols:
                    val = str(row.get(col, ""))
                    unique_vals = sorted(set(str(r.get(col, "")) for r in data))
                    for uv in unique_vals:
                        new_row[f"{col}_{uv}"] = 1 if val == uv else 0
                new_data.append(new_row)
            data = new_data

        final_cols = list(data[0].keys()) if data else []
        return data, StepResult(
            self.name, len(cols), len(final_cols), len(data), len(data),
            columns_modified=cat_cols,
        )


class NumericScaler(BaseTransformer):
    """Step 6: Scale numeric features."""

    @property
    def name(self) -> str:
        return "numeric_scaler"

    def fit_transform(self, data: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], StepResult]:
        method = config.get("method", "standard")  # standard, minmax, log

        if not data:
            return data, StepResult(self.name, 0, 0, 0, 0)

        cols = list(data[0].keys())
        modified: list[str] = []

        for col in cols:
            try:
                values = [float(row[col]) for row in data if row.get(col) is not None]
            except (ValueError, TypeError):
                continue

            if len(values) < 2:
                continue

            arr = np.array(values)

            if method == "standard":
                mean, std = np.mean(arr), np.std(arr)
                if std > 0:
                    for row in data:
                        try:
                            row[col] = round((float(row[col]) - mean) / std, 6)
                        except (ValueError, TypeError):
                            pass
                    modified.append(col)

            elif method == "minmax":
                mn, mx = np.min(arr), np.max(arr)
                rng = mx - mn
                if rng > 0:
                    for row in data:
                        try:
                            row[col] = round((float(row[col]) - mn) / rng, 6)
                        except (ValueError, TypeError):
                            pass
                    modified.append(col)

            elif method == "log":
                for row in data:
                    try:
                        val = float(row[col])
                        row[col] = round(float(np.log1p(max(val, 0))), 6)
                    except (ValueError, TypeError):
                        pass
                modified.append(col)

        return data, StepResult(
            self.name, len(cols), len(cols), len(data), len(data),
            columns_modified=modified,
        )


class NearZeroVarianceRemoval(BaseTransformer):
    """Step 7: Post-encoding near-zero variance cleanup."""

    @property
    def name(self) -> str:
        return "near_zero_variance"

    def fit_transform(self, data: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], StepResult]:
        min_variance = config.get("min_variance", 0.01)

        if not data:
            return data, StepResult(self.name, 0, 0, 0, 0)

        cols = list(data[0].keys())
        cols_to_remove: list[str] = []

        for col in cols:
            try:
                values = [float(row[col]) for row in data]
                if np.var(values) < min_variance:
                    cols_to_remove.append(col)
            except (ValueError, TypeError):
                pass

        result_data = [{k: v for k, v in row.items() if k not in cols_to_remove} for row in data]
        remaining = list(result_data[0].keys()) if result_data else []

        return result_data, StepResult(
            self.name, len(cols), len(remaining), len(data), len(result_data),
            columns_removed=cols_to_remove,
        )


# ── Pipeline Orchestrator ────────────────────────────────

DEFAULT_STEPS: list[BaseTransformer] = [
    UniqueRatioFilter(),
    LowInfoRemoval(),
    MissingValueImputer(),
    OutlierTreatment(),
    CategoricalEncoder(),
    NumericScaler(),
    NearZeroVarianceRemoval(),
]


@dataclass
class CleaningReport:
    """Full report from the 7-step cleaning pipeline."""

    steps: list[StepResult]
    original_shape: tuple[int, int]
    final_shape: tuple[int, int]
    columns_removed_total: list[str]
    columns_modified_total: list[str]


def run_cleaning_pipeline(
    data: list[dict[str, Any]],
    config: dict[str, dict[str, Any]] | None = None,
    steps: list[BaseTransformer] | None = None,
) -> tuple[list[dict[str, Any]], CleaningReport]:
    """Execute the 7-step cleaning pipeline.

    Args:
        data: Raw data as list of row dicts.
        config: Per-step configuration. Keys are step names.
        steps: Custom step list (defaults to all 7 steps).

    Returns:
        (cleaned_data, CleaningReport)
    """
    if config is None:
        config = {}
    if steps is None:
        steps = DEFAULT_STEPS

    original_rows = len(data)
    original_cols = len(data[0]) if data else 0

    all_results: list[StepResult] = []
    all_removed: list[str] = []
    all_modified: list[str] = []
    current_data = [dict(row) for row in data]  # Deep copy

    for step in steps:
        step_config = config.get(step.name, {})
        current_data, result = step.fit_transform(current_data, step_config)
        all_results.append(result)
        all_removed.extend(result.columns_removed)
        all_modified.extend(result.columns_modified)

    final_rows = len(current_data)
    final_cols = len(current_data[0]) if current_data else 0

    report = CleaningReport(
        steps=all_results,
        original_shape=(original_rows, original_cols),
        final_shape=(final_rows, final_cols),
        columns_removed_total=list(set(all_removed)),
        columns_modified_total=list(set(all_modified)),
    )

    return current_data, report
