from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.collectors.news import EventRegistryNewsCollector
from backend.kyc.store import load_layer1_baselines
from backend.models import Layer1KycBaseline, RawSignal
from backend.replay import load_raw_signals, model_to_json_dict, write_jsonl, write_raw_signals
from stream_engine.drift_engine import KeywordDriftEngine


DEFAULT_REPLAY_DIR = Path("data/layer1_replay")
MOCK_NEWS_QUERY_COST_UNITS = 0.0
LIVE_NEWS_QUERY_COST_UNITS = 1.0


def run_layer1(client_id: str, limit: int, live: bool = False, replay_file: str | None = None) -> list[dict]:
    return run_layer1_pipeline(
        client_id=client_id,
        limit=limit,
        live=live,
        replay_file=replay_file,
    )["drift_events"]


def run_layer1_pipeline(
    client_id: str,
    limit: int,
    live: bool = False,
    replay_file: str | None = None,
) -> dict[str, Any]:
    baselines = load_layer1_baselines()
    baseline = baselines[client_id]
    signals = _load_or_collect_signals(
        baseline=baseline,
        limit=limit,
        live=live,
        replay_file=replay_file,
    )
    drift_engine = KeywordDriftEngine()

    events = []
    dropped_signals = []
    for signal in signals:
        event = drift_engine.score_signal(baseline, signal)
        if event:
            events.append(model_to_json_dict(event))
        else:
            dropped_signals.append(
                {
                    "client_id": signal.client_id,
                    "entity_name": signal.entity_name,
                    "signal_type": signal.signal_type.value
                    if hasattr(signal.signal_type, "value")
                    else str(signal.signal_type),
                    "source": signal.source,
                    "title": str(signal.metadata.get("title", signal.content.splitlines()[0])),
                    "drop_reason": "stable_below_drift_threshold",
                    "timestamp": signal.timestamp.isoformat(),
                }
            )
    return {
        "drift_events": events,
        "raw_signals": signals,
        "dropped_signals": dropped_signals,
        "layer1_metrics": _build_layer1_metrics(
            client_id=client_id,
            signals=signals,
            events=events,
            dropped_signals=dropped_signals,
            live=live,
            replay_file=replay_file,
        ),
    }


def _load_or_collect_signals(
    baseline: Layer1KycBaseline,
    limit: int,
    live: bool,
    replay_file: str | None,
) -> list[RawSignal]:
    if replay_file:
        return load_raw_signals(replay_file, client_id=baseline.client_id)[:limit]

    news_collector = EventRegistryNewsCollector(enabled=live)
    return news_collector.fetch_company_news(
        client_id=baseline.client_id,
        company_name=baseline.legal_name,
        limit=limit,
    )


def _write_replay_outputs(output_dir: str | Path, payload: dict[str, Any]) -> None:
    replay_dir = Path(output_dir)
    write_raw_signals(replay_dir / "raw_signals.jsonl", payload["raw_signals"])
    write_jsonl(replay_dir / "drift_events.jsonl", payload["drift_events"])
    write_jsonl(replay_dir / "dropped_signals.jsonl", payload["dropped_signals"])
    write_jsonl(replay_dir / "layer1_metrics.jsonl", [payload["layer1_metrics"]])


def _build_layer1_metrics(
    client_id: str,
    signals: list[RawSignal],
    events: list[dict[str, Any]],
    dropped_signals: list[dict[str, Any]],
    live: bool,
    replay_file: str | None,
) -> dict[str, Any]:
    processed = len(signals)
    emitted = len(events)
    dropped = len(dropped_signals)
    news_queries = 0 if replay_file else 1
    news_query_cost_units = LIVE_NEWS_QUERY_COST_UNITS if live and not replay_file else MOCK_NEWS_QUERY_COST_UNITS
    estimated_cost_units = news_queries * news_query_cost_units
    return {
        "schema_version": "layer1.metrics.v1",
        "client_id": client_id,
        "mode": "replay" if replay_file else "live" if live else "mock",
        "signals_processed": processed,
        "signals_dropped": dropped,
        "events_emitted": emitted,
        "drop_rate": round(dropped / processed, 4) if processed else 0.0,
        "emission_rate": round(emitted / processed, 4) if processed else 0.0,
        "news_queries": news_queries,
        "llm_tokens": 0,
        "heavy_reasoner_calls": 0,
        "estimated_cost_units": estimated_cost_units,
        "estimated_cost_units_per_1000_analyses": round(
            (estimated_cost_units / processed) * 1000,
            4,
        )
        if processed
        else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Layer 1 public intelligence drift detection.")
    parser.add_argument("--client-id", default="demo-spacex-001")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--live", action="store_true", help="Allow live Event Registry calls. Defaults to mock/replay only.")
    parser.add_argument("--replay-file", help="Read RawSignal records from a JSONL replay file instead of collecting news.")
    parser.add_argument(
        "--write-replay-dir",
        nargs="?",
        const=str(DEFAULT_REPLAY_DIR),
        help="Write raw_signals.jsonl, drift_events.jsonl, and dropped_signals.jsonl.",
    )
    args = parser.parse_args()

    payload = run_layer1_pipeline(
        client_id=args.client_id,
        limit=args.limit,
        live=args.live,
        replay_file=args.replay_file,
    )
    if args.write_replay_dir:
        _write_replay_outputs(args.write_replay_dir, payload)
    print(
        json.dumps(
            {
                "drift_events": payload["drift_events"],
                "layer1_metrics": payload["layer1_metrics"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
