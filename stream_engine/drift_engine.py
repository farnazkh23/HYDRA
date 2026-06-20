from __future__ import annotations

import hashlib

from backend.models import DriftEvent, DriftSeverity, Layer1KycBaseline, RawSignal


class KeywordDriftEngine:
    """Cheap Layer 1 gate that emits only meaningful KYC drift events."""

    def score_signal(self, baseline: Layer1KycBaseline, signal: RawSignal) -> DriftEvent | None:
        text = signal.content.lower()
        matched_risk_terms = [term for term in baseline.high_risk_keywords if term.lower() in text]
        matched_expected_terms = [term for term in baseline.expected_keywords if term.lower() in text]
        missing_baseline_terms = [
            term for term in baseline.expected_keywords if term not in matched_expected_terms
        ]

        risk_term_score = min(0.75, 0.18 * len(matched_risk_terms))
        baseline_mismatch_score = min(0.2, 0.04 * len(missing_baseline_terms))
        entity_score = 0.1 if baseline.legal_name.lower() in text else 0.0
        drift_score = round(min(1.0, risk_term_score + baseline_mismatch_score + entity_score), 3)
        scoring_breakdown = {
            "risk_term_score": round(risk_term_score, 3),
            "baseline_mismatch_score": round(baseline_mismatch_score, 3),
            "entity_match_score": round(entity_score, 3),
            "source_recency_score": 0.0,
            "source_reliability_score": 0.0,
        }

        if drift_score < 0.35:
            return None

        severity = (
            DriftSeverity.CRITICAL
            if drift_score >= 0.85
            else DriftSeverity.HIGH
            if drift_score >= 0.65
            else DriftSeverity.MEDIUM
        )
        rationale = (
            f"Public signal deviates from baseline '{baseline.baseline_business_model}'. "
            f"Matched risk terms: {', '.join(matched_risk_terms) or 'none'}."
        )
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
            source_metadata={
                "raw_signal_id": str(signal.metadata.get("signal_id", "")),
                "signal_type": signal.signal_type.value
                if hasattr(signal.signal_type, "value")
                else str(signal.signal_type),
                "source": signal.source,
                "provider": str(signal.metadata.get("provider", "")),
                "entity_name": signal.entity_name,
            },
            layer1_cost_units={
                "news_queries": 1.0,
                "llm_tokens": 0.0,
                "heavy_reasoner_calls": 0.0,
            },
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
