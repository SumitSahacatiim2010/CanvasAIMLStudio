"""Drift Detection Service — monitors distribution shifts between training and production data.

Uses statistical tests (KS-test, Chi-square) to identify feature and label drift.
Blueprint §3.4: Drift detection is critical for model maintenance.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from scipy import stats


@dataclass
class FeatureDrift:
    """Drift analysis for a single feature."""
    feature_name: str
    drift_score: float  # p-value or distance metric
    is_drifted: bool
    method: str
    message: str


@dataclass
class DriftReport:
    """Full drift report for a model."""
    model_id: str
    overall_drift_score: float
    drift_status: str  # none, low, moderate, high
    feature_drifts: List[FeatureDrift]
    timestamp: str


class DriftDetectionService:
    """Detects data and model drift using statistical divergence tests."""

    def __init__(self, p_value_threshold: float = 0.05, psi_threshold: float = 0.2):
        self.p_value_threshold = p_value_threshold
        self.psi_threshold = psi_threshold

    def generate_reference_stats(self, data: List[Dict[str, Any]], features: List[str], buckets: int = 10) -> Dict[str, Any]:
        """Generate summary statistics and distributions for a baseline dataset."""
        stats_out = {}
        for feature in features:
            values = [row.get(feature) for row in data if row.get(feature) is not None]
            if not values:
                continue

            try:
                # Numeric path
                numeric_vals = np.array([float(v) for v in values])
                if len(numeric_vals) == 0:
                    continue
                    
                min_v, max_v = numeric_vals.min(), numeric_vals.max()
                bins = np.linspace(min_v, max_v, buckets + 1)
                counts, _ = np.histogram(numeric_vals, bins=bins)
                probs = counts / len(numeric_vals)
                
                # Use bin edges as strings for JSON keys
                dist = {f"{bins[i]:.4f}_{bins[i+1]:.4f}": float(probs[i]) for i in range(len(probs))}
                
                stats_out[feature] = {
                    "type": "numeric",
                    "mean": float(numeric_vals.mean()),
                    "std": float(numeric_vals.std()),
                    "min": float(min_v),
                    "max": float(max_v),
                    "bins": bins.tolist(),
                    "distribution": dist
                }
            except (ValueError, TypeError):
                # Categorical path
                from collections import Counter
                counts = Counter(values)
                total = len(values)
                dist = {str(k): float(v / total) for k, v in counts.items()}
                
                stats_out[feature] = {
                    "type": "categorical",
                    "distribution": dist
                }
        return stats_out

    def calculate_psi(self, expected: List[Any], actual: List[Any], buckets: int = 10) -> float:
        """Calculate Population Stability Index (PSI).
        
        PSI = sum((Actual % - Expected %) * ln(Actual % / Expected %))
        """
        # Determine if data is categorical
        try:
            # Try to treat as numeric
            exp_vals = np.array([float(v) for v in expected if v is not None])
            act_vals = np.array([float(v) for v in actual if v is not None])
            
            if len(exp_vals) == 0 or len(act_vals) == 0:
                return 0.0

            # Create bins based on expected data
            min_val = min(exp_vals.min(), act_vals.min())
            max_val = max(exp_vals.max(), act_vals.max())
            bins = np.linspace(min_val, max_val, buckets + 1)
            
            exp_counts, _ = np.histogram(exp_vals, bins=bins)
            act_counts, _ = np.histogram(act_vals, bins=bins)
            
            exp_p = exp_counts / len(exp_vals)
            act_p = act_counts / len(act_vals)
            
        except (ValueError, TypeError):
            # Categorical path
            from collections import Counter
            exp_counts_dict = Counter(expected)
            act_counts_dict = Counter(actual)
            
            all_cats = set(exp_counts_dict.keys()) | set(act_counts_dict.keys())
            exp_total = len(expected)
            act_total = len(actual)
            
            exp_p = np.array([exp_counts_dict[cat] / exp_total for cat in all_cats])
            act_p = np.array([act_counts_dict[cat] / act_total for cat in all_cats])

        # Avoid division by zero and log of zero
        exp_p = np.where(exp_p == 0, 0.0001, exp_p)
        act_p = np.where(act_p == 0, 0.0001, act_p)
        
        psi = np.sum((act_p - exp_p) * np.log(act_p / exp_p))
        return float(psi)

    def calculate_psi_from_stats(self, reference_feature_stats: Dict[str, Any], actual: List[Any]) -> float:
        """Calculate PSI using pre-calculated reference stats (handles numeric bins or categorical)."""
        if not reference_feature_stats or not actual:
            return 0.0
            
        f_type = reference_feature_stats.get("type", "categorical")
        expected_dist = reference_feature_stats.get("distribution", {})
        
        if f_type == "numeric" and "bins" in reference_feature_stats:
            # Numeric path: bin the actual data using reference bins
            bins = np.array(reference_feature_stats["bins"])
            numeric_act = np.array([float(v) for v in actual if v is not None])
            if len(numeric_act) == 0:
                return 0.0
                
            act_counts, _ = np.histogram(numeric_act, bins=bins)
            act_p = act_counts / len(numeric_act)
            
            # expected_dist keys are "bin_start_bin_end", values are probs
            # We align act_p with expected_dist values
            exp_p = np.array([expected_dist.get(f"{bins[i]:.4f}_{bins[i+1]:.4f}", 0.0) for i in range(len(bins)-1)])
        else:
            # Categorical path
            from collections import Counter
            act_counts_dict = Counter(actual)
            act_total = len(actual)
            
            all_cats = list(set(expected_dist.keys()) | set(str(k) for k in act_counts_dict.keys()))
            exp_p = np.array([expected_dist.get(cat, 0.0) for cat in all_cats])
            act_p = np.array([act_counts_dict.get(cat if not cat.isdigit() else int(cat), 0.0) / act_total for cat in all_cats])
            # Note: str conversion in set union and get() might need care for numeric categories
        
        # Avoid division by zero and log of zero
        exp_p = np.where(exp_p <= 0, 0.0001, exp_p)
        act_p = np.where(act_p <= 0, 0.0001, act_p)
        
        psi = np.sum((act_p - exp_p) * np.log(act_p / exp_p))
        return float(psi)

    def detect_drift(
        self,
        current_data: List[Dict[str, Any]],
        features: List[str],
        model_id: str,
        reference_data: Optional[List[Dict[str, Any]]] = None,
        reference_stats: Optional[Dict[str, Any]] = None
    ) -> DriftReport:
        """Analyze drift across specified features using raw data or stats."""
        if not current_data or (not reference_data and not reference_stats):
            return DriftReport(
                model_id=model_id,
                overall_drift_score=0.0,
                drift_status="none",
                feature_drifts=[],
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        feature_drifts = []
        drifted_count = 0

        for feature in features:
            curr_values = [row.get(feature) for row in current_data if row.get(feature) is not None]
            if not curr_values:
                continue

            # Path A: Using raw reference data
            if reference_data:
                ref_values = [row.get(feature) for row in reference_data if row.get(feature) is not None]
                if not ref_values:
                    continue
                    
                psi_score = self.calculate_psi(ref_values, curr_values)
                
                try:
                    ref_numeric = [float(v) for v in ref_values]
                    curr_numeric = [float(v) for v in curr_values]
                    ks_stat, p_value = stats.ks_2samp(ref_numeric, curr_numeric)
                    is_drifted = (p_value < self.p_value_threshold) or (psi_score > self.psi_threshold)
                    method = "KS + PSI"
                    msg = f"Shift detected (PSI={psi_score:.2f}, p={p_value:.4f})" if is_drifted else "Stable"
                except (ValueError, TypeError):
                    is_drifted = psi_score > self.psi_threshold
                    method = "PSI-Categorical"
                    msg = f"Categorical shift (PSI={psi_score:.2f})" if is_drifted else "Stable"

            # Path B: Using pre-calculated stats (distributions)
            elif reference_stats and feature in reference_stats:
                f_stats = reference_stats[feature]
                psi_score = self.calculate_psi_from_stats(f_stats, curr_values)
                
                is_drifted = psi_score > self.psi_threshold
                method = "PSI (from stats)"
                msg = f"Shift detected via stats (PSI={psi_score:.2f})" if is_drifted else "Stable"
            else:
                continue

            fd = FeatureDrift(
                feature_name=feature,
                drift_score=round(psi_score, 4),
                is_drifted=is_drifted,
                method=method,
                message=msg
            )
            feature_drifts.append(fd)
            if fd.is_drifted:
                drifted_count += 1

        # Determine overall status
        drift_ratio = drifted_count / len(feature_drifts) if feature_drifts else 0
        if drift_ratio == 0:
            status = "none"
        elif drift_ratio < 0.2:
            status = "low"
        elif drift_ratio < 0.5:
            status = "moderate"
        else:
            status = "high"

        return DriftReport(
            model_id=model_id,
            overall_drift_score=round(drift_ratio, 2),
            drift_status=status,
            feature_drifts=feature_drifts,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
