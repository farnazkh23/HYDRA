from __future__ import annotations

from dataclasses import dataclass

from backend.models import Layer1KycBaseline
from stream_engine.vectorizer import DenseFeatureVector, HybridFeatureVector, SparseFeatureVector


@dataclass(frozen=True)
class ReconstructionResult:
    """VAE-compatible gate output for Loop A regime-shift decisions."""

    engine: str
    reconstruction_error: float
    drift_threshold: float
    dynamic_variance: float
    drift_detected: bool
    decision: str
    nominal_profile: dict[str, float | int | str]


class VAECompatibleReconstructionEngine:
    """Safe proxy with the same contract a future lightweight VAE should expose."""

    def evaluate(
        self,
        baseline: Layer1KycBaseline,
        sparse_features: SparseFeatureVector,
        dense_features: DenseFeatureVector,
        hybrid_features: HybridFeatureVector,
        heuristic_score: float,
        threshold_floor: float,
    ) -> ReconstructionResult:
        nominal_profile = _fit_nominal_profile(baseline)
        reconstruction_error = round(
            min(
                1.0,
                heuristic_score
                + _risk_activation_bonus(sparse_features)
                + _semantic_residual_bonus(dense_features, hybrid_features),
            ),
            3,
        )
        drift_threshold = round(
            max(
                threshold_floor,
                nominal_profile["nominal_mean"] + (2 * nominal_profile["nominal_std"]),
            ),
            3,
        )
        drift_detected = reconstruction_error >= drift_threshold
        return ReconstructionResult(
            engine="vae_compatible_statistical_proxy",
            reconstruction_error=reconstruction_error,
            drift_threshold=drift_threshold,
            dynamic_variance=round(nominal_profile["nominal_std"] ** 2, 4),
            drift_detected=drift_detected,
            decision="DRIFT_EVENT emitted" if drift_detected else "Signal dropped — stable",
            nominal_profile=nominal_profile,
        )


def _fit_nominal_profile(baseline: Layer1KycBaseline) -> dict[str, float | int | str]:
    expected_signal_count = max(1, len(baseline.expected_keywords) + len(baseline.expected_activity))
    nominal_mean = 0.12 if baseline.risk_rating == "low" else 0.14 if baseline.risk_rating == "medium" else 0.18
    nominal_std = min(0.12, max(0.06, 1 / (expected_signal_count * 2)))
    return {
        "fit_mode": "baseline_profile_proxy",
        "expected_signal_count": expected_signal_count,
        "nominal_mean": round(nominal_mean, 3),
        "nominal_std": round(nominal_std, 3),
    }


def _risk_activation_bonus(sparse_features: SparseFeatureVector) -> float:
    if not sparse_features.matched_risk_terms:
        return 0.0
    return min(0.06, 0.015 * len(sparse_features.matched_risk_terms))


def _semantic_residual_bonus(
    dense_features: DenseFeatureVector,
    hybrid_features: HybridFeatureVector,
) -> float:
    if hybrid_features.sparse_activation_ratio < 0.5:
        return 0.0
    return min(0.04, max(0.0, dense_features.semantic_shift_score - 0.65) * 0.1)
