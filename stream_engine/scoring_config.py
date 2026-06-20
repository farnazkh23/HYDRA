from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SCORING_CONFIG_PATH = Path("config/layer1_scoring.json")


@dataclass(frozen=True)
class Layer1Thresholds:
    emit_event: float
    high: float
    critical: float


@dataclass(frozen=True)
class Layer1Weights:
    risk_term: float
    risk_term_cap: float
    baseline_mismatch: float
    baseline_mismatch_cap: float
    entity_match: float
    adverse_sentiment_multiplier: float
    adverse_sentiment_cap: float


@dataclass(frozen=True)
class Layer1ScoringConfig:
    thresholds: Layer1Thresholds
    weights: Layer1Weights


def load_layer1_scoring_config(path: str | Path = DEFAULT_SCORING_CONFIG_PATH) -> Layer1ScoringConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return Layer1ScoringConfig(
        thresholds=Layer1Thresholds(**payload["thresholds"]),
        weights=Layer1Weights(**payload["weights"]),
    )
