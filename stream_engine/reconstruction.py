from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from pathlib import Path

from backend.models import Layer1KycBaseline
from stream_engine.vae_snapshots import load_nominal_snapshots
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


class LightweightVAEReconstructionEngine:
    """Tiny local VAE trained on nominal baseline feature samples."""

    def __init__(self, snapshot_dir: str | Path | None = None) -> None:
        import numpy as np

        self._np = np
        self.snapshot_dir = snapshot_dir
        self._pca_fallback = LocalPCAReconstructionEngine()

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
        baseline_samples = _nominal_feature_samples(nominal_profile)
        time_series_snapshots = load_nominal_snapshots(
            client_id=baseline.client_id,
            snapshot_dir=self.snapshot_dir,
        )
        samples = self._np.asarray([*baseline_samples, *time_series_snapshots], dtype=float)
        train_samples, validation_samples = _train_validation_split(samples, validation_ratio=0.2)
        feature_vector = self._np.asarray(
            build_reconstruction_feature_vector(
                sparse_features=sparse_features,
                dense_features=dense_features,
                hybrid_features=hybrid_features,
                heuristic_score=heuristic_score,
            ),
            dtype=float,
        )
        model = self._fit_vae(train_samples)
        validation_losses = [
            self._reconstruction_loss(validation_sample, model)
            for validation_sample in validation_samples
        ]
        validation_mean = float(self._np.mean(validation_losses))
        validation_std = float(self._np.std(validation_losses))
        learned_threshold = validation_mean + (2 * validation_std)
        vae_loss = self._reconstruction_loss(feature_vector, model)
        vae_error = min(1.0, vae_loss * 8)
        fallback = self._pca_fallback.evaluate(
            baseline=baseline,
            sparse_features=sparse_features,
            dense_features=dense_features,
            hybrid_features=hybrid_features,
            heuristic_score=heuristic_score,
            threshold_floor=threshold_floor,
        )
        if not sparse_features.matched_risk_terms:
            return ReconstructionResult(
                engine="lightweight_vae_reconstruction",
                reconstruction_error=fallback.reconstruction_error,
                drift_threshold=fallback.drift_threshold,
                dynamic_variance=fallback.dynamic_variance,
                drift_detected=fallback.drift_detected,
                decision=fallback.decision,
                nominal_profile={
                    **nominal_profile,
                    "fit_mode": "lightweight_vae_baseline_80_20",
                    "latent_dimensions": 2,
                    "train_samples": len(train_samples),
                    "validation_samples": len(validation_samples),
                    "start_point_samples": len(baseline_samples),
                    "time_series_snapshots": len(time_series_snapshots),
                    "validation_loss_mean": round(validation_mean, 4),
                    "validation_loss_std": round(validation_std, 4),
                    "vae_loss": round(vae_loss, 4),
                    "safety_gate": "no_risk_terms_used_pca_fallback",
                },
            )

        drift_threshold = round(max(threshold_floor, min(0.95, learned_threshold * 8)), 3)
        reconstruction_error = round(max(fallback.reconstruction_error, vae_error), 3)
        drift_detected = reconstruction_error >= drift_threshold
        return ReconstructionResult(
            engine="lightweight_vae_reconstruction",
            reconstruction_error=reconstruction_error,
            drift_threshold=drift_threshold,
            dynamic_variance=round(validation_std**2, 4),
            drift_detected=drift_detected,
            decision="DRIFT_EVENT emitted" if drift_detected else "Signal dropped — stable",
            nominal_profile={
                **nominal_profile,
                "fit_mode": "lightweight_vae_baseline_80_20",
                "latent_dimensions": 2,
                "train_samples": len(train_samples),
                "validation_samples": len(validation_samples),
                "start_point_samples": len(baseline_samples),
                "time_series_snapshots": len(time_series_snapshots),
                "validation_loss_mean": round(validation_mean, 4),
                "validation_loss_std": round(validation_std, 4),
                "vae_loss": round(vae_loss, 4),
                "fallback_engine": fallback.engine,
            },
        )

    def _fit_vae(self, train_samples: object) -> dict[str, object]:
        np = self._np
        rng = np.random.default_rng(7)
        input_dimensions = train_samples.shape[1]
        latent_dimensions = 2
        model = {
            "w_mu": rng.normal(0, 0.08, size=(input_dimensions, latent_dimensions)),
            "b_mu": np.zeros(latent_dimensions),
            "w_logvar": rng.normal(0, 0.02, size=(input_dimensions, latent_dimensions)),
            "b_logvar": np.zeros(latent_dimensions),
            "w_decoder": rng.normal(0, 0.08, size=(latent_dimensions, input_dimensions)),
            "b_decoder": train_samples.mean(axis=0),
        }
        learning_rate = 0.08
        beta = 0.03
        for _ in range(220):
            mu = train_samples @ model["w_mu"] + model["b_mu"]
            logvar = np.clip(train_samples @ model["w_logvar"] + model["b_logvar"], -4, 4)
            reconstruction = mu @ model["w_decoder"] + model["b_decoder"]
            reconstruction_grad = 2 * (reconstruction - train_samples) / train_samples.size
            decoder_grad = mu.T @ reconstruction_grad
            decoder_bias_grad = reconstruction_grad.sum(axis=0)
            mu_grad = reconstruction_grad @ model["w_decoder"].T
            mu_grad += beta * mu / len(train_samples)
            logvar_grad = beta * 0.5 * (np.exp(logvar) - 1) / len(train_samples)

            model["w_decoder"] -= learning_rate * decoder_grad
            model["b_decoder"] -= learning_rate * decoder_bias_grad
            model["w_mu"] -= learning_rate * (train_samples.T @ mu_grad)
            model["b_mu"] -= learning_rate * mu_grad.sum(axis=0)
            model["w_logvar"] -= learning_rate * (train_samples.T @ logvar_grad)
            model["b_logvar"] -= learning_rate * logvar_grad.sum(axis=0)
        return model

    def _reconstruction_loss(self, feature_vector: object, model: dict[str, object]) -> float:
        np = self._np
        vector = np.asarray(feature_vector, dtype=float)
        mu = vector @ model["w_mu"] + model["b_mu"]
        reconstruction = mu @ model["w_decoder"] + model["b_decoder"]
        return float(np.mean((reconstruction - vector) ** 2))


def build_default_reconstruction_engine(
    snapshot_dir: str | Path | None = None,
) -> (
    LightweightVAEReconstructionEngine | LocalPCAReconstructionEngine | VAECompatibleReconstructionEngine
):
    try:
        return LightweightVAEReconstructionEngine(snapshot_dir=snapshot_dir)
    except Exception:
        pass
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


def build_reconstruction_feature_vector(
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


def _feature_vector(
    sparse_features: SparseFeatureVector,
    dense_features: DenseFeatureVector,
    hybrid_features: HybridFeatureVector,
    heuristic_score: float,
) -> list[float]:
    return build_reconstruction_feature_vector(
        sparse_features=sparse_features,
        dense_features=dense_features,
        hybrid_features=hybrid_features,
        heuristic_score=heuristic_score,
    )


def _nominal_feature_samples(nominal_profile: dict[str, float | int | str]) -> list[list[float]]:
    nominal_mean = float(nominal_profile["nominal_mean"])
    nominal_std = float(nominal_profile["nominal_std"])
    return [
        [0.0, 0.1, 0.3, 0.08, nominal_mean, nominal_mean, nominal_mean],
        [0.0, 0.2, 0.3, 0.1, nominal_mean + nominal_std, nominal_mean, nominal_mean],
        [0.0, 0.1, 0.6, 0.12, nominal_mean, nominal_mean + nominal_std, nominal_mean],
        [0.0, 0.2, 0.6, 0.14, nominal_mean + nominal_std, nominal_mean + nominal_std, nominal_mean],
        [0.0, 0.0, 0.3, 0.08, max(0.0, nominal_mean - nominal_std), nominal_mean, nominal_mean],
        [0.0, 0.1, 0.4, 0.1, nominal_mean, max(0.0, nominal_mean - nominal_std), nominal_mean],
        [0.0, 0.0, 0.6, 0.09, max(0.0, nominal_mean - nominal_std), nominal_mean, nominal_mean],
        [0.0, 0.2, 0.4, 0.11, nominal_mean, nominal_mean, nominal_mean + nominal_std],
        [0.0, 0.1, 0.3, 0.07, nominal_mean + nominal_std, nominal_mean, max(0.0, nominal_mean - nominal_std)],
        [0.0, 0.0, 0.4, 0.08, nominal_mean, nominal_mean, max(0.0, nominal_mean - nominal_std)],
    ]


def _train_validation_split(samples: object, validation_ratio: float) -> tuple[object, object]:
    validation_count = max(1, round(len(samples) * validation_ratio))
    split_index = len(samples) - validation_count
    return samples[:split_index], samples[split_index:]
