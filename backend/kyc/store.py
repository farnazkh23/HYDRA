from __future__ import annotations

import json
from pathlib import Path

from backend.models import Layer1KycBaseline


DEFAULT_PROFILE_PATH = Path(__file__).with_name("profiles.json")
DEFAULT_RISK_TERMS_PATH = Path(__file__).parents[2] / "config" / "layer1_risk_terms.json"


def load_layer1_baselines(
    path: str | Path = DEFAULT_PROFILE_PATH,
    risk_terms_path: str | Path = DEFAULT_RISK_TERMS_PATH,
) -> dict[str, Layer1KycBaseline]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    risk_terms = _load_risk_terms(risk_terms_path)
    baselines = [
        Layer1KycBaseline(
            **{
                **client,
                "high_risk_keywords": _dedupe_terms(
                    [
                        *risk_terms["global_high_risk_keywords"],
                        *risk_terms["persona_high_risk_keywords"].get(client["client_id"], []),
                        *client.get("high_risk_keywords", []),
                    ]
                ),
            }
        )
        for client in payload["clients"]
    ]
    return {baseline.client_id: baseline for baseline in baselines}


def _load_risk_terms(path: str | Path) -> dict[str, object]:
    risk_terms_file = Path(path)
    if not risk_terms_file.exists():
        return {"global_high_risk_keywords": [], "persona_high_risk_keywords": {}}
    payload = json.loads(risk_terms_file.read_text(encoding="utf-8"))
    return {
        "global_high_risk_keywords": payload.get("global_high_risk_keywords", []),
        "persona_high_risk_keywords": payload.get("persona_high_risk_keywords", {}),
    }


def _dedupe_terms(terms: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for term in terms:
        normalized = term.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            deduped.append(normalized)
    return deduped
