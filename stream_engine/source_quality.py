from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.models import RawSignal, SignalType


HIGH_RELIABILITY_SOURCES = [
    "reuters",
    "associated press",
    "ap news",
    "bloomberg",
    "financial times",
    "wall street journal",
    "dow jones",
    "sec",
    "department of justice",
    "court",
    "regulator",
    "official",
]

MEDIUM_RELIABILITY_SOURCES = [
    "yahoo",
    "nasdaq",
    "marketwatch",
    "the street",
    "thestreet",
    "texas public radio",
    "event_registry",
]


@dataclass(frozen=True)
class SourceQualityScores:
    recency_score: float
    reliability_score: float
    signal_type_score: float


def score_source_quality(signal: RawSignal, now: datetime | None = None) -> SourceQualityScores:
    evaluated_at = now or datetime.now(timezone.utc)
    return SourceQualityScores(
        recency_score=_recency_score(signal, evaluated_at),
        reliability_score=_reliability_score(signal),
        signal_type_score=_signal_type_score(signal),
    )


def _recency_score(signal: RawSignal, now: datetime) -> float:
    published_at = _published_at(signal)
    age_days = max(0.0, (now - published_at).total_seconds() / 86_400)
    if age_days <= 1:
        return 1.0
    if age_days <= 7:
        return 0.8
    if age_days <= 30:
        return 0.55
    if age_days <= 90:
        return 0.3
    return 0.1


def _reliability_score(signal: RawSignal) -> float:
    source_text = " ".join(
        [
            signal.source,
            str(signal.metadata.get("provider", "")),
            str(signal.metadata.get("source", "")),
            str(signal.metadata.get("url", "")),
        ]
    ).lower()
    if any(source in source_text for source in HIGH_RELIABILITY_SOURCES):
        return 0.9
    if any(source in source_text for source in MEDIUM_RELIABILITY_SOURCES):
        return 0.7
    if signal.source.startswith("mock_"):
        return 0.6
    if str(signal.metadata.get("provider", "")) == "event_registry":
        return 0.65
    return 0.5


def _signal_type_score(signal: RawSignal) -> float:
    signal_type = signal.signal_type.value if hasattr(signal.signal_type, "value") else str(signal.signal_type)
    if signal_type == SignalType.NEWS.value:
        return 0.7
    if signal_type in {SignalType.REGISTRY.value, SignalType.DOMAIN_CHANGE.value}:
        return 0.85
    if signal_type == SignalType.FUNDING.value:
        return 0.75
    if signal_type == SignalType.TRANSACTION.value:
        return 0.65
    return 0.5


def _published_at(signal: RawSignal) -> datetime:
    raw_value = signal.metadata.get("published_at")
    if isinstance(raw_value, str) and raw_value:
        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    timestamp = signal.timestamp
    return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
