from __future__ import annotations

import argparse
import json

from backend.collectors.news import EventRegistryNewsCollector
from backend.kyc.store import load_layer1_baselines
from stream_engine.drift_engine import KeywordDriftEngine


def run_layer1(client_id: str, limit: int) -> list[dict]:
    baselines = load_layer1_baselines()
    baseline = baselines[client_id]
    news_collector = EventRegistryNewsCollector()
    drift_engine = KeywordDriftEngine()

    signals = news_collector.fetch_company_news(
        client_id=baseline.client_id,
        company_name=baseline.legal_name,
        limit=limit,
    )
    events = []
    for signal in signals:
        event = drift_engine.score_signal(baseline, signal)
        if event:
            events.append(_model_to_json_dict(event))
    return events


def _model_to_json_dict(model: object) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")  # type: ignore[attr-defined]
    if hasattr(model, "json"):
        return json.loads(model.json())  # type: ignore[attr-defined]
    raise TypeError(f"Unsupported model type: {type(model)!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Layer 1 public intelligence drift detection.")
    parser.add_argument("--client-id", default="demo-aminaclient-001")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    events = run_layer1(client_id=args.client_id, limit=args.limit)
    print(json.dumps({"drift_events": events}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
