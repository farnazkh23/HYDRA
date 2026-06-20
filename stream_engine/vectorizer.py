from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

from backend.models import Layer1KycBaseline, RawSignal


HASH_EMBEDDING_DIMENSIONS = 32
ONNX_MODEL_PATH_ENV = "LAYER1_ONNX_MODEL_PATH"
ONNX_TOKENIZER_PATH_ENV = "LAYER1_ONNX_TOKENIZER_PATH"


@dataclass(frozen=True)
class SparseFeatureVector:
    """Local weighted sparse activations for cheap Layer 1 keyword/entity filtering."""

    encoder: str
    matched_risk_terms: list[str]
    matched_expected_terms: list[str]
    missing_baseline_terms: list[str]
    matched_entities: list[str]
    activations: dict[str, float]

    @property
    def activation_count(self) -> int:
        return len([value for value in self.activations.values() if value > 0.0])


class SparseSignalVectorizer:
    """SPLADE-style local sparse encoder using weighted keyword/entity activations."""

    encoder = "local_splade_style_sparse"

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
            **{
                f"risk::{term}": _activation_weight(term, text, base_weight=1.0)
                for term in matched_risk_terms
            },
            **{
                f"expected::{term}": _activation_weight(term, text, base_weight=0.7)
                for term in matched_expected_terms
            },
            **{f"missing_expected::{term}": 0.35 for term in missing_baseline_terms},
            **{
                f"entity::{entity}": _activation_weight(entity, text, base_weight=0.9)
                for entity in matched_entities
            },
        }
        return SparseFeatureVector(
            encoder=self.encoder,
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


class LocalTfidfDenseVectorizer:
    """Local sklearn TF-IDF dense path; falls back outside when sklearn is unavailable."""

    encoder = "local_tfidf_embedding"

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        self._tfidf_vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=256,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9-]{2,}\b",
        )
        self._cosine_similarity = cosine_similarity

    def encode(self, baseline: Layer1KycBaseline, signal: RawSignal) -> DenseFeatureVector:
        baseline_text = _baseline_text(baseline)
        matrix = self._tfidf_vectorizer.fit_transform([baseline_text, signal.content])
        similarity = float(self._cosine_similarity(matrix[0], matrix[1])[0][0])
        semantic_shift_score = max(0.0, min(1.0, 1.0 - similarity))
        return DenseFeatureVector(
            encoder=self.encoder,
            dimensions=len(self._tfidf_vectorizer.vocabulary_),
            baseline_similarity=round(similarity, 3),
            semantic_shift_score=round(semantic_shift_score, 3),
            signal_norm=round(_sparse_vector_norm(matrix[1]), 3),
            baseline_norm=round(_sparse_vector_norm(matrix[0]), 3),
        )


class LocalOnnxTransformerDenseVectorizer:
    """Optional local ONNX transformer embedding path for Notion-aligned dense encoding."""

    encoder = "local_onnx_transformer"

    def __init__(self, model_path: str | Path, tokenizer_path: str | Path | None = None) -> None:
        import numpy as np
        import onnxruntime as ort
        from transformers import AutoTokenizer

        resolved_model_path = Path(model_path).expanduser()
        if not resolved_model_path.exists():
            raise FileNotFoundError(f"ONNX model not found: {resolved_model_path}")

        resolved_tokenizer_path = Path(tokenizer_path).expanduser() if tokenizer_path else resolved_model_path.parent
        if not resolved_tokenizer_path.exists():
            raise FileNotFoundError(f"ONNX tokenizer not found: {resolved_tokenizer_path}")

        self._np = np
        self._tokenizer = AutoTokenizer.from_pretrained(str(resolved_tokenizer_path), local_files_only=True)
        self._session = ort.InferenceSession(str(resolved_model_path), providers=["CPUExecutionProvider"])
        self._input_names = {input_meta.name for input_meta in self._session.get_inputs()}

    def encode(self, baseline: Layer1KycBaseline, signal: RawSignal) -> DenseFeatureVector:
        baseline_vector = self._embed(_baseline_text(baseline))
        signal_vector = self._embed(signal.content)
        similarity = _cosine_similarity(baseline_vector, signal_vector)
        semantic_shift_score = max(0.0, min(1.0, 1.0 - similarity))
        return DenseFeatureVector(
            encoder=self.encoder,
            dimensions=len(signal_vector),
            baseline_similarity=round(similarity, 3),
            semantic_shift_score=round(semantic_shift_score, 3),
            signal_norm=round(_vector_norm(signal_vector), 3),
            baseline_norm=round(_vector_norm(baseline_vector), 3),
        )

    def _embed(self, text: str) -> list[float]:
        encoded = self._tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="np",
        )
        inputs = {name: value for name, value in encoded.items() if name in self._input_names}
        outputs = self._session.run(None, inputs)
        embedding = self._pool_output(outputs[0], encoded.get("attention_mask"))
        norm = float(self._np.linalg.norm(embedding))
        if norm > 0:
            embedding = embedding / norm
        return [float(value) for value in embedding.tolist()]

    def _pool_output(self, output: object, attention_mask: object | None) -> object:
        array = self._np.asarray(output)
        if array.ndim == 2:
            return array[0]
        if array.ndim != 3:
            return array.reshape(-1)

        token_embeddings = array[0]
        if attention_mask is None:
            return token_embeddings.mean(axis=0)

        mask = self._np.asarray(attention_mask)[0].reshape(-1, 1)
        masked_embeddings = token_embeddings * mask
        return masked_embeddings.sum(axis=0) / max(float(mask.sum()), 1.0)


class DenseVectorizerWithRuntimeFallback:
    """Uses a primary dense encoder but falls back locally if inference fails."""

    def __init__(
        self,
        primary: LocalOnnxTransformerDenseVectorizer,
        fallback: LocalTfidfDenseVectorizer | LocalHashingDenseVectorizer,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.encoder = primary.encoder

    def encode(self, baseline: Layer1KycBaseline, signal: RawSignal) -> DenseFeatureVector:
        try:
            return self.primary.encode(baseline, signal)
        except Exception:
            return self.fallback.encode(baseline, signal)


def build_default_dense_vectorizer() -> (
    DenseVectorizerWithRuntimeFallback
    | LocalOnnxTransformerDenseVectorizer
    | LocalTfidfDenseVectorizer
    | LocalHashingDenseVectorizer
):
    fallback_vectorizer = _build_local_dense_fallback()
    onnx_model_path = os.getenv(ONNX_MODEL_PATH_ENV)
    if onnx_model_path:
        try:
            return DenseVectorizerWithRuntimeFallback(
                primary=LocalOnnxTransformerDenseVectorizer(
                    model_path=onnx_model_path,
                    tokenizer_path=os.getenv(ONNX_TOKENIZER_PATH_ENV),
                ),
                fallback=fallback_vectorizer,
            )
        except Exception:
            pass
    return fallback_vectorizer


def _build_local_dense_fallback() -> LocalTfidfDenseVectorizer | LocalHashingDenseVectorizer:
    try:
        return LocalTfidfDenseVectorizer()
    except Exception:
        return LocalHashingDenseVectorizer()


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


def _activation_weight(term: str, text: str, base_weight: float) -> float:
    count = max(1, text.count(term.lower()))
    return round(min(1.0, base_weight * (1 + math.log(count))), 3)


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


def _sparse_vector_norm(vector: object) -> float:
    return math.sqrt(float(vector.multiply(vector).sum()))
