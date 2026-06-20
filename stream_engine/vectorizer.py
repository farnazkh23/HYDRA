from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from backend.models import Layer1KycBaseline, RawSignal


HASH_EMBEDDING_DIMENSIONS = 32


@dataclass(frozen=True)
class SparseFeatureVector:
    """Exact local activations for cheap Layer 1 keyword/entity filtering."""

    matched_risk_terms: list[str]
    matched_expected_terms: list[str]
    missing_baseline_terms: list[str]
    matched_entities: list[str]
    activations: dict[str, float]

    @property
    def activation_count(self) -> int:
        return len([value for value in self.activations.values() if value > 0.0])


class SparseSignalVectorizer:
    """Lightweight SPLADE-style placeholder using exact public-signal activations."""

    def encode(self, baseline: Layer1KycBaseline, signal: RawSignal) -> SparseFeatureVector:
        text = signal.content.lower()
        matched_risk_terms = _matched_terms(baseline.high_risk_keywords, text)
        matched_expected_terms = _matched_terms(baseline.expected_keywords, text)
        missing_baseline_terms = [
            term for term in baseline.expected_keywords if term not in matched_expected_terms
        ]
        candidate_entities = [
            baseline.legal_name,
            *baseline.monitored_public_entities,
            *signal.metadata.get("related_entities", []),
        ]
        matched_entities = _dedupe(_matched_terms(candidate_entities, text))

        activations = {
            **{f"risk::{term}": 1.0 for term in matched_risk_terms},
            **{f"expected::{term}": 1.0 for term in matched_expected_terms},
            **{f"missing_expected::{term}": 1.0 for term in missing_baseline_terms},
            **{f"entity::{entity}": 1.0 for entity in matched_entities},
        }
        return SparseFeatureVector(
            matched_risk_terms=matched_risk_terms,
            matched_expected_terms=matched_expected_terms,
            missing_baseline_terms=missing_baseline_terms,
            matched_entities=matched_entities,
            activations=activations,
        )


@dataclass(frozen=True)
class DenseFeatureVector:
    """Cheap local semantic proxy for future ONNX transformer embeddings."""

    encoder: str
    dimensions: int
    baseline_similarity: float
    semantic_shift_score: float
    signal_norm: float
    baseline_norm: float


class LocalHashingDenseVectorizer:
    """Deterministic hashing embedding so Layer 1 has a no-API dense path."""

    def __init__(self, dimensions: int = HASH_EMBEDDING_DIMENSIONS) -> None:
        self.dimensions = dimensions

    def encode(self, baseline: Layer1KycBaseline, signal: RawSignal) -> DenseFeatureVector:
        baseline_text = _baseline_text(baseline)
        baseline_vector = _hashing_vector(baseline_text, self.dimensions)
        signal_vector = _hashing_vector(signal.content, self.dimensions)
        similarity = _cosine_similarity(baseline_vector, signal_vector)
        semantic_shift_score = max(0.0, min(1.0, 1.0 - similarity))
        return DenseFeatureVector(
            encoder="local_hashing_embedding",
            dimensions=self.dimensions,
            baseline_similarity=round(similarity, 3),
            semantic_shift_score=round(semantic_shift_score, 3),
            signal_norm=round(_vector_norm(signal_vector), 3),
            baseline_norm=round(_vector_norm(baseline_vector), 3),
        )


@dataclass(frozen=True)
class HybridFeatureVector:
    """Combined sparse+dense representation for the Loop A gate."""

    encoder: str
    sparse_dimensions: int
    dense_dimensions: int
    hybrid_dimensions: int
    sparse_activation_ratio: float
    semantic_shift_score: float
    hybrid_shift_score: float
    feature_families: list[str]


class HybridSignalVectorizer:
    """Composes exact sparse activations with cheap local dense semantic features."""

    def encode(
        self,
        sparse_features: SparseFeatureVector,
        dense_features: DenseFeatureVector,
    ) -> HybridFeatureVector:
        sparse_dimensions = len(sparse_features.activations)
        dense_dimensions = dense_features.dimensions
        sparse_activation_ratio = min(1.0, sparse_features.activation_count / 10)
        hybrid_shift_score = round(
            min(
                1.0,
                (0.45 * sparse_activation_ratio)
                + (0.55 * dense_features.semantic_shift_score),
            ),
            3,
        )
        return HybridFeatureVector(
            encoder="local_sparse_dense_hybrid",
            sparse_dimensions=sparse_dimensions,
            dense_dimensions=dense_dimensions,
            hybrid_dimensions=sparse_dimensions + dense_dimensions,
            sparse_activation_ratio=round(sparse_activation_ratio, 3),
            semantic_shift_score=dense_features.semantic_shift_score,
            hybrid_shift_score=hybrid_shift_score,
            feature_families=["risk_terms", "baseline_terms", "entities", "semantic_hash"],
        )


def _matched_terms(terms: list[str], text: str) -> list[str]:
    return [term for term in _dedupe(terms) if term.lower() in text]


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        normalized = value.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            deduped.append(normalized)
    return deduped


def _baseline_text(baseline: Layer1KycBaseline) -> str:
    return " ".join(
        [
            baseline.legal_name,
            baseline.baseline_business_model,
            " ".join(baseline.expected_activity),
            " ".join(baseline.expected_keywords),
            " ".join(baseline.expected_jurisdictions),
            baseline.expected_transaction_profile,
            baseline.risk_appetite,
            baseline.domain,
        ]
    )


def _hashing_vector(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = _vector_norm(vector)
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())]


def _cosine_similarity(left_vector: list[float], right_vector: list[float]) -> float:
    left_norm = _vector_norm(left_vector)
    right_norm = _vector_norm(right_vector)
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(
        left_value * right_value
        for left_value, right_value in zip(left_vector, right_vector)
    ) / (left_norm * right_norm)


def _vector_norm(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))
