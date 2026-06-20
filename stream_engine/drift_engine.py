from __future__ import annotations

import hashlib

from backend.models import DriftEvent, DriftSeverity, Layer1KycBaseline, RawSignal
from stream_engine.relevance import evaluate_relevance
from pathlib import Path

from stream_engine.reconstruction import build_default_reconstruction_engine, build_reconstruction_feature_vector
from stream_engine.relationship_context import extract_relationship_context
from stream_engine.scoring_config import Layer1ScoringConfig, load_layer1_scoring_config
from stream_engine.source_quality import score_source_quality
from stream_engine.vectorizer import (
    HybridSignalVectorizer,
    SparseSignalVectorizer,
    build_default_dense_vectorizer,
)


class KeywordDriftEngine:
    """Cheap Layer 1 gate that emits only meaningful KYC drift events."""

    def __init__(
        self,
        scoring_config: Layer1ScoringConfig | None = None,
        vae_snapshot_dir: str | Path | None = None,
    ) -> None:
        self.scoring_config = scoring_config or load_layer1_scoring_config()
        self.sparse_vectorizer = SparseSignalVectorizer()
        self.dense_vectorizer = build_default_dense_vectorizer()
        self.hybrid_vectorizer = HybridSignalVectorizer()
        self.reconstruction_engine = build_default_reconstruction_engine(snapshot_dir=vae_snapshot_dir)

    def score_signal(self, baseline: Layer1KycBaseline, signal: RawSignal) -> DriftEvent | None:
        weights = self.scoring_config.weights
        thresholds = self.scoring_config.thresholds
        relevance = evaluate_relevance(baseline, signal)
        if not relevance.relevant:
            return None

        text = signal.content.lower()
        sparse_features = self.sparse_vectorizer.encode(baseline, signal)
        dense_features = self.dense_vectorizer.encode(baseline, signal)
        hybrid_features = self.hybrid_vectorizer.encode(sparse_features, dense_features)
        matched_risk_terms = sparse_features.matched_risk_terms
        missing_baseline_terms = sparse_features.missing_baseline_terms

        risk_term_score = min(weights.risk_term_cap, weights.risk_term * len(matched_risk_terms))
        baseline_mismatch_score = min(
            weights.baseline_mismatch_cap,
            weights.baseline_mismatch * len(missing_baseline_terms),
        )
        entity_score = weights.entity_match if baseline.legal_name.lower() in text else 0.0
        sentiment_value = _safe_float(signal.metadata.get("sentiment_score"))
        adverse_sentiment_score = _adverse_sentiment_score(sentiment_value, self.scoring_config)
        source_quality = score_source_quality(signal)
        heuristic_score = round(
            min(1.0, risk_term_score + baseline_mismatch_score + entity_score + adverse_sentiment_score),
            3,
        )
        reconstruction_result = self.reconstruction_engine.evaluate(
            baseline=baseline,
            sparse_features=sparse_features,
            dense_features=dense_features,
            hybrid_features=hybrid_features,
            heuristic_score=heuristic_score,
            threshold_floor=thresholds.emit_event,
        )
        drift_score = reconstruction_result.reconstruction_error
        embedding_shift_score = dense_features.semantic_shift_score
        scoring_breakdown = {
            "risk_term_score": round(risk_term_score, 3),
            "baseline_mismatch_score": round(baseline_mismatch_score, 3),
            "entity_match_score": round(entity_score, 3),
            "relevance_score": relevance.score,
            "adverse_sentiment_score": round(adverse_sentiment_score, 3),
            "dense_semantic_shift_score": dense_features.semantic_shift_score,
            "hybrid_shift_score": hybrid_features.hybrid_shift_score,
            "heuristic_score": heuristic_score,
            "reconstruction_error": reconstruction_result.reconstruction_error,
            "dynamic_threshold": reconstruction_result.drift_threshold,
            "source_recency_score": source_quality.recency_score,
            "source_reliability_score": source_quality.reliability_score,
            "signal_type_score": source_quality.signal_type_score,
        }

        if not reconstruction_result.drift_detected:
            return None

        severity = (
            DriftSeverity.CRITICAL
            if drift_score >= thresholds.critical
            else DriftSeverity.HIGH
            if drift_score >= thresholds.high
            else DriftSeverity.MEDIUM
        )
        rationale = (
            f"Public signal deviates from baseline '{baseline.baseline_business_model}'. "
            f"Matched risk terms: {', '.join(matched_risk_terms) or 'none'}."
        )
        relationship_context = extract_relationship_context(signal, primary_entity=baseline.legal_name)
        return DriftEvent(
            event_id=_event_id(baseline.client_id, str(signal.metadata.get("signal_id", signal.content))),
            client_id=baseline.client_id,
            client_name=baseline.legal_name,
            severity=severity,
            drift_score=drift_score,
            routing_hint="layer2_structural_reasoning"
            if severity in {DriftSeverity.HIGH, DriftSeverity.CRITICAL}
            else "layer2_fast_classifier",
            matched_risk_terms=matched_risk_terms,
            missing_baseline_terms=missing_baseline_terms,
            scoring_breakdown=scoring_breakdown,
            rationale=rationale,
            recommended_action=_recommended_action(severity),
            citations=[
                {
                    "title": str(signal.metadata.get("title", signal.content.splitlines()[0])),
                    "url": str(signal.metadata.get("url", "")),
                    "published_at": str(signal.metadata.get("published_at", signal.timestamp.isoformat())),
                    "source": signal.source,
                }
            ],
            loop_a_trace={
                "trace_mode": "vae_compatible_proxy",
                "reconstruction_engine": reconstruction_result.engine,
                "vae_reconstruction_error": reconstruction_result.reconstruction_error,
                "drift_threshold": reconstruction_result.drift_threshold,
                "dynamic_variance": reconstruction_result.dynamic_variance,
                "drift_score": drift_score,
                "drift_detected": reconstruction_result.drift_detected,
                "relevance_gate": {
                    "relevant": relevance.relevant,
                    "score": relevance.score,
                    "matched_terms": relevance.matched_terms,
                    "reason": relevance.reason,
                },
                "top_keywords_matched": matched_risk_terms,
                "embedding_shift_score": embedding_shift_score,
                "decision": reconstruction_result.decision,
                "tokens_used": 0,
                "cost_usd": 0.0,
                "nominal_profile": reconstruction_result.nominal_profile,
                "sparse_encoder": {
                    "encoder": sparse_features.encoder,
                    "weighting": "log_tf_keyword_entity",
                    "activation_count": sparse_features.activation_count,
                    "matched_entities": sparse_features.matched_entities,
                    "activations": sparse_features.activations,
                },
                "dense_encoder": {
                    "encoder": dense_features.encoder,
                    "dimensions": dense_features.dimensions,
                    "baseline_similarity": dense_features.baseline_similarity,
                    "semantic_shift_score": dense_features.semantic_shift_score,
                    "signal_norm": dense_features.signal_norm,
                    "baseline_norm": dense_features.baseline_norm,
                },
                "hybrid_encoder": {
                    "encoder": hybrid_features.encoder,
                    "sparse_dimensions": hybrid_features.sparse_dimensions,
                    "dense_dimensions": hybrid_features.dense_dimensions,
                    "hybrid_dimensions": hybrid_features.hybrid_dimensions,
                    "sparse_activation_ratio": hybrid_features.sparse_activation_ratio,
                    "semantic_shift_score": hybrid_features.semantic_shift_score,
                    "hybrid_shift_score": hybrid_features.hybrid_shift_score,
                    "feature_families": hybrid_features.feature_families,
                },
            },
            source_metadata={
                "raw_signal_id": str(signal.metadata.get("signal_id", "")),
                "signal_type": signal.signal_type.value
                if hasattr(signal.signal_type, "value")
                else str(signal.signal_type),
                "source": signal.source,
                "provider": str(signal.metadata.get("provider", "")),
                "entity_name": signal.entity_name,
                "sentiment_score": sentiment_value,
                "relevance_matched_terms": relevance.matched_terms,
                "source_recency_score": source_quality.recency_score,
                "source_reliability_score": source_quality.reliability_score,
                "signal_type_score": source_quality.signal_type_score,
                **relationship_context,
            },
            layer1_cost_units={
                "news_queries": 1.0,
                "llm_tokens": 0.0,
                "heavy_reasoner_calls": 0.0,
            },
        )

    def nominal_snapshot_for_signal(
        self,
        baseline: Layer1KycBaseline,
        signal: RawSignal,
    ) -> list[float] | None:
        relevance = evaluate_relevance(baseline, signal)
        if not relevance.relevant:
            return None

        sparse_features = self.sparse_vectorizer.encode(baseline, signal)
        if sparse_features.matched_risk_terms:
            return None

        dense_features = self.dense_vectorizer.encode(baseline, signal)
        hybrid_features = self.hybrid_vectorizer.encode(sparse_features, dense_features)
        weights = self.scoring_config.weights
        text = signal.content.lower()
        baseline_mismatch_score = min(
            weights.baseline_mismatch_cap,
            weights.baseline_mismatch * len(sparse_features.missing_baseline_terms),
        )
        entity_score = weights.entity_match if baseline.legal_name.lower() in text else 0.0
        sentiment_value = _safe_float(signal.metadata.get("sentiment_score"))
        adverse_sentiment_score = _adverse_sentiment_score(sentiment_value, self.scoring_config)
        heuristic_score = round(
            min(1.0, baseline_mismatch_score + entity_score + adverse_sentiment_score),
            3,
        )
        if heuristic_score >= self.scoring_config.thresholds.emit_event:
            return None

        return build_reconstruction_feature_vector(
            sparse_features=sparse_features,
            dense_features=dense_features,
            hybrid_features=hybrid_features,
            heuristic_score=heuristic_score,
        )


def _recommended_action(severity: DriftSeverity) -> str:
    if severity == DriftSeverity.CRITICAL:
        return "Immediate compliance escalation; freeze automated risk downgrade until analyst review."
    if severity == DriftSeverity.HIGH:
        return "Trigger enhanced due diligence and route to Layer 2 structural reasoning."
    return "Queue for AML/KYC analyst review and continue public-signal monitoring."


def _event_id(client_id: str, signal_id: str) -> str:
    digest = hashlib.sha256(f"{client_id}:{signal_id}".encode("utf-8")).hexdigest()
    return f"drift_{digest[:16]}"


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _adverse_sentiment_score(sentiment: float | None, scoring_config: Layer1ScoringConfig) -> float:
    if sentiment is None or sentiment >= 0:
        return 0.0
    weights = scoring_config.weights
    return min(weights.adverse_sentiment_cap, abs(sentiment) * weights.adverse_sentiment_multiplier)
