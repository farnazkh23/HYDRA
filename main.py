# main.py
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import pandas as pd

# --- LAYER 1 INFRASTRUCTURE IMPORTS ---
from backend.collectors.news import EventRegistryNewsCollector, dedupe_signals
from backend.kyc.store import load_layer1_baselines
from backend.models import Layer1KycBaseline, RawSignal
from backend.replay import load_raw_signals, model_to_json_dict, write_jsonl, write_raw_signals
from stream_engine.drift_engine import KeywordDriftEngine
from stream_engine.relevance import evaluate_relevance

# --- LAYER 2 ANALYTIC INFRASTRUCTURE IMPORTS ---
from analytic_engine.datasets import ComplianceMultiModalDataset
from analytic_engine.graph_fusion import KnowledgeTriple, StructuralResolutionPayload, TemporalGraphFusionEngine
from analytic_engine.models import BaseSurvivalModel
from analytic_engine.router import CostAwareCascadingRouter
from analytic_engine.time_series import InternalTelemetryEngine

DEFAULT_REPLAY_DIR = Path("data/layer1_replay")
LIVE_NEWS_QUERY_COST_UNITS = 1.0
MOCK_NEWS_QUERY_COST_UNITS = 0.0


# --- LAYER 2 MULTI-MODAL PIPELINE ORCHESTRATOR ---
async def execute_hydra_pipeline(drift_event: dict[str, Any], transaction_history: pd.DataFrame):
    """
    Main Event-Driven Loop B Orchestrator.
    Consumes the stable Loop A 'DRIFT_EVENT' contract payload natively.
    """
    client_id = drift_event.get("client_id", "UNKNOWN")
    client_name = drift_event.get("client_name", "Unknown Entity")
    print(f"\n⚡ [Hydra Core Action] Processing pipeline ingestion payload for customer: {client_name} ({client_id})")

    # 1. Map Layer 1 Relationship Hints and Metadata into Knowledge Triples
    source_meta = drift_event.get("source_metadata", {})
    hints = source_meta.get("relationship_hints", [])
    roles = source_meta.get("entity_roles", {})

    incoming_triples = []
    for entity, role in roles.items():
        if role != "monitored_client":
            predicate = hints[0].upper() if hints else "ASSOCIATED_WITH"
            mod = "ADDED" if drift_event.get("severity") in ["high", "critical"] else "UNCHANGED"
            incoming_triples.append(
                KnowledgeTriple(subject=client_name, predicate=predicate, object=entity, modification_type=mod)
            )

    # If Layer 1 extracted no explicit roles, build a contextual default from matched risk indicators
    if not incoming_triples:
        incoming_triples = [
            KnowledgeTriple(
                subject=client_name,
                predicate="HAS_RISK_INDICATOR",
                object=str(drift_event.get("matched_risk_terms", ["Divergent_Profile"])[0]).title(),
                modification_type="ADDED",
            )
        ]

    # 2. Run Live Layer 2 Internal Telemetry Checking
    ts_engine = InternalTelemetryEngine()
    _, ts_metrics = ts_engine.detect_volumetric_anomaly(transaction_history)

    # 3. Run Local/Cloud Temporal Graph Fusion Update
    graph_engine = TemporalGraphFusionEngine()
    payload = StructuralResolutionPayload(
        chain_of_thought=f"Analyzing edge structural mutations from ingestion against baseline KYC topology. Layer 1 drift score: {drift_event.get('drift_score')}",
        detected_triples=incoming_triples,
    )
    graph_metrics = graph_engine.execute_triple_resolution(payload, timestamp=drift_event.get("triggered_at"))
    graph_engine.close()

    # 4. Vectorize Through Automated Imputation Layers
    data_assembler = ComplianceMultiModalDataset()
    matrix_X = data_assembler.impute_and_vectorize(ts_metrics, graph_metrics)

    # 5. Compute Continuous Deep Survival Horizon Timeline
    survival_model = BaseSurvivalModel()
    predicted_t, uncertainty = survival_model.calculate_time_to_decay(matrix_X)

    # 6. Route Through Budget-Aware Guardrailed Output Layer (Sovereign Swiss Apertus AI)
    raw_context_signal = f"Rationale: {drift_event.get('rationale')}. Detected Terms: {drift_event.get('matched_risk_terms')}. Severity: {drift_event.get('severity')}"
    router = CostAwareCascadingRouter()
    final_audit_log = router.evaluate_routing_tier(client_id, predicted_t, raw_context_signal)

    # 7. Merge Layer 1 Source Citations into Final Legal Registry Audit Ledger
    layer1_citations = [c.get("url", "Internal Source") for c in drift_event.get("citations", [])]
    all_citations = list(set(final_audit_log.audit_citations + layer1_citations))

    print("\n================== DEFINITIVE AUDIT LOG OUTPUT ==================")
    print(f"Risk Rating Token : {final_audit_log.risk_token}")
    print(f"Compliance Audit  : {final_audit_log.chain_of_thought}")
    print(f"Source Citations  : {all_citations}")
    print(f"Pipeline Budget   : {router.token_ledger}")
    print("=================================================================\n")
    return final_audit_log


# --- LAYER 1 WORKING INFRASTRUCTURE ---
def run_layer1(client_id: str, limit: int, live: bool = False, replay_file: str | None = None) -> list[dict]:
    return run_layer1_pipeline(client_id=client_id, limit=limit, live=live, replay_file=replay_file)["drift_events"]


def run_layer1_pipeline(
        client_id: str,
        limit: int,
        live: bool = False,
        replay_file: str | None = None,
        expand_adverse_news: bool = False,
) -> dict[str, Any]:
    baselines = load_layer1_baselines()
    baseline = baselines[client_id]
    signals, news_queries = _load_or_collect_signals(
        baseline=baseline,
        limit=limit,
        live=live,
        replay_file=replay_file,
        expand_adverse_news=expand_adverse_news,
    )
    signals = dedupe_signals(signals)
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
                    "drop_reason": _drop_reason(baseline, signal),
                    "timestamp": signal.timestamp.isoformat(),
                }
            )
    _assign_event_cost_units(
        events=events,
        live=live,
        replay_file=replay_file,
        news_queries=news_queries,
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
            news_queries=news_queries,
        ),
    }


def _load_or_collect_signals(
        baseline: Layer1KycBaseline,
        limit: int,
        live: bool,
        replay_file: str | None,
        expand_adverse_news: bool,
) -> tuple[list[RawSignal], int]:
    if replay_file:
        return load_raw_signals(replay_file, client_id=baseline.client_id)[:limit], 0

    news_collector = EventRegistryNewsCollector(
        enabled=live,
        expand_adverse_queries=expand_adverse_news,
    )
    signals = news_collector.fetch_company_news(
        client_id=baseline.client_id,
        company_name=baseline.legal_name,
        limit=limit,
    )
    return signals, news_collector.last_query_count if live else 0


def _drop_reason(baseline: Layer1KycBaseline, signal: RawSignal) -> str:
    relevance = evaluate_relevance(baseline, signal)
    if not relevance.relevant:
        return relevance.reason
    return "stable_below_drift_threshold"


def _write_replay_outputs(output_dir: str | Path, payload: dict[str, Any]) -> None:
    replay_dir = Path(output_dir)
    write_raw_signals(replay_dir / "raw_signals.jsonl", payload["raw_signals"])
    write_jsonl(replay_dir / "drift_events.jsonl", payload["drift_events"])
    write_jsonl(replay_dir / "dropped_signals.jsonl", payload["dropped_signals"])
    write_jsonl(replay_dir / "layer1_metrics.jsonl", [payload["layer1_metrics"]])


def _assign_event_cost_units(
        events: list[dict[str, Any]],
        live: bool,
        replay_file: str | None,
        news_queries: int,
) -> None:
    if not events:
        return
    news_query_cost = 0.0
    if live and not replay_file:
        news_query_cost = round(news_queries / len(events), 4)
    for event in events:
        event["layer1_cost_units"] = {
            "news_queries": news_query_cost,
            "llm_tokens": 0.0,
            "heavy_reasoner_calls": 0.0,
        }


def _build_layer1_metrics(
        client_id: str,
        signals: list[RawSignal],
        events: list[dict[str, Any]],
        dropped_signals: list[dict[str, Any]],
        live: bool,
        replay_file: str | None,
        news_queries: int,
) -> dict[str, Any]:
    processed = len(signals)
    emitted = len(events)
    dropped = len(dropped_signals)
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


# --- MAIN UNIFIED ENTRY POINT ---
def main() -> None:
    parser = argparse.ArgumentParser(description="Run Layer 1 public intelligence drift detection.")
    parser.add_argument("--client-id", default="demo-spacex-001")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--live", action="store_true", help="Allow live Event Registry calls. Defaults to mock/replay only."
    )
    parser.add_argument(
        "--expand-adverse-news",
        action="store_true",
        help="In live mode, query additional adverse Event Registry searches for the same client.",
    )
    parser.add_argument(
        "--replay-file", help="Read RawSignal records from a JSONL replay file instead of collecting news."
    )
    parser.add_argument(
        "--write-replay-dir",
        nargs="?",
        const=str(DEFAULT_REPLAY_DIR),
        help="Write raw_signals.jsonl, drift_events.jsonl, and dropped_signals.jsonl.",
    )
    args = parser.parse_args()

    # 1. Execute upstream Layer 1 data ingestion
    payload = run_layer1_pipeline(
        client_id=args.client_id,
        limit=args.limit,
        live=args.live,
        replay_file=args.replay_file,
        expand_adverse_news=args.expand_adverse_news,
    )

    if args.write_replay_dir:
        _write_replay_outputs(args.write_replay_dir, payload)

    # Print baseline tracking metrics as expected by Layer 1 contracts
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

    # 2. Feed emitted Layer 1 drift events directly into Layer 2 Deep Analytics
    drift_events = payload["drift_events"]

    if not drift_events:
        print("\n✅ Layer 1 Scan Complete: No profile anomalies crossed threshold boundaries.")
        return

    # Build transaction time-series history data frame mapping to dormancy break metrics
    dates = pd.date_range(start="2026-05-01", end="2026-06-20", freq="D")
    volumes = [150 if i < (len(dates) - 1) else 2500000 for i in range(len(dates))]
    history_df = pd.DataFrame({"timestamp": dates, "value": volumes})

    # Sequentially cascade high-risk events through the active multi-modal survival loops
    for event in drift_events:
        asyncio.run(execute_hydra_pipeline(event, history_df))


if __name__ == "__main__":
    main()