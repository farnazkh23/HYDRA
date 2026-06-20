from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

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


class LocalPCAReconstructionEngine:
    """Small fitted reconstruction model that keeps the future VAE contract stable."""

    def __init__(self) -> None:
        from sklearn.decomposition import PCA

        self._pca_cls = PCA
        self._statistical_fallback = VAECompatibleReconstructionEngine()

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
        nominal_samples = _nominal_feature_samples(nominal_profile)
        feature_vector = _feature_vector(
            sparse_features=sparse_features,
            dense_features=dense_features,
            hybrid_features=hybrid_features,
            heuristic_score=heuristic_score,
        )
        pca = self._pca_cls(n_components=2, random_state=7)
        pca.fit(nominal_samples)
        reconstructed = pca.inverse_transform(pca.transform([feature_vector]))[0]
        mse = sum(
            (actual - predicted) ** 2
            for actual, predicted in zip(feature_vector, reconstructed)
        ) / len(feature_vector)
        pca_error = min(1.0, sqrt(mse) * 3)
        fallback = self._statistical_fallback.evaluate(
            baseline=baseline,
            sparse_features=sparse_features,
            dense_features=dense_features,
            hybrid_features=hybrid_features,
            heuristic_score=heuristic_score,
            threshold_floor=threshold_floor,
        )
        if not sparse_features.matched_risk_terms:
            return ReconstructionResult(
                engine="local_pca_reconstruction",
                reconstruction_error=fallback.reconstruction_error,
                drift_threshold=fallback.drift_threshold,
                dynamic_variance=fallback.dynamic_variance,
                drift_detected=fallback.drift_detected,
                decision=fallback.decision,
                nominal_profile={
                    **nominal_profile,
                    "fit_mode": "local_pca_baseline_proxy",
                    "pca_components": 2,
                    "pca_error": round(pca_error, 3),
                    "safety_gate": "no_risk_terms_used_statistical_fallback",
                },
            )
        reconstruction_error = round(max(fallback.reconstruction_error, pca_error), 3)
        drift_detected = reconstruction_error >= fallback.drift_threshold
        return ReconstructionResult(
            engine="local_pca_reconstruction",
            reconstruction_error=reconstruction_error,
            drift_threshold=fallback.drift_threshold,
            dynamic_variance=fallback.dynamic_variance,
            drift_detected=drift_detected,
            decision="DRIFT_EVENT emitted" if drift_detected else "Signal dropped — stable",
            nominal_profile={
                **nominal_profile,
                "fit_mode": "local_pca_baseline_proxy",
                "pca_components": 2,
                "pca_error": round(pca_error, 3),
            },
        )


def build_default_reconstruction_engine() -> LocalPCAReconstructionEngine | VAECompatibleReconstructionEngine:
    try:
        return LocalPCAReconstructionEngine()
    except Exception:
        return VAECompatibleReconstructionEngine()


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


def _feature_vector(
    sparse_features: SparseFeatureVector,
    dense_features: DenseFeatureVector,
    hybrid_features: HybridFeatureVector,
    heuristic_score: float,
) -> list[float]:
    return [
        min(1.0, len(sparse_features.matched_risk_terms) / 5),
        min(1.0, len(sparse_features.missing_baseline_terms) / 5),
        min(1.0, len(sparse_features.matched_entities) / 3),
        sparse_features.activation_count / max(1, hybrid_features.hybrid_dimensions),
        dense_features.semantic_shift_score,
        hybrid_features.hybrid_shift_score,
        heuristic_score,
    ]


def _nominal_feature_samples(nominal_profile: dict[str, float | int | str]) -> list[list[float]]:
    nominal_mean = float(nominal_profile["nominal_mean"])
    nominal_std = float(nominal_profile["nominal_std"])
    return [
        [0.0, 0.1, 0.3, 0.08, nominal_mean, nominal_mean, nominal_mean],
        [0.0, 0.2, 0.3, 0.1, nominal_mean + nominal_std, nominal_mean, nominal_mean],
        [0.0, 0.1, 0.6, 0.12, nominal_mean, nominal_mean + nominal_std, nominal_mean],
        [0.0, 0.2, 0.6, 0.14, nominal_mean + nominal_std, nominal_mean + nominal_std, nominal_mean],
        [0.0, 0.0, 0.3, 0.08, max(0.0, nominal_mean - nominal_std), nominal_mean, nominal_mean],
    ]
