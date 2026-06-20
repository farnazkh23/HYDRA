from __future__ import annotations

from dataclasses import dataclass

from backend.models import Layer1KycBaseline, RawSignal


@dataclass(frozen=True)
class RelevanceDecision:
    relevant: bool
    score: float
    matched_terms: list[str]
    reason: str


def evaluate_relevance(baseline: Layer1KycBaseline, signal: RawSignal) -> RelevanceDecision:
    """Cheap pre-gate that rejects public signals unrelated to the monitored client."""
    searchable_text = " ".join(
        [
            signal.content,
            str(signal.metadata.get("title", "")),
            " ".join(str(entity) for entity in signal.metadata.get("related_entities", [])),
        ]
    ).lower()
    candidate_terms = _dedupe(
        [
            baseline.legal_name,
            *baseline.monitored_public_entities,
            baseline.domain,
        ]
    )
    matched_terms = [
        term for term in candidate_terms
        if term and term.lower() in searchable_text
    ]
    score = round(min(1.0, len(matched_terms) / 2), 3)
    if matched_terms:
        return RelevanceDecision(
            relevant=True,
            score=score,
            matched_terms=matched_terms,
            reason="matched_monitored_entity",
        )
    return RelevanceDecision(
        relevant=False,
        score=0.0,
        matched_terms=[],
        reason="irrelevant_to_monitored_client",
    )


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
