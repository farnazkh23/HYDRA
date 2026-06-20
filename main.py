# main.py
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

# --- LAYER 1 INFRASTRUCTURE IMPORTS ---
from backend.audit import append_layer1_audit_record
from backend.collectors.news import EventRegistryNewsCollector, dedupe_signals
from backend.kyc.store import load_layer1_baselines
from backend.models import Layer1KycBaseline, RawSignal
from backend.replay import load_raw_signals, model_to_json_dict, write_jsonl, write_raw_signals
from stream_engine.drift_engine import KeywordDriftEngine
from stream_engine.relevance import evaluate_relevance
from stream_engine.vae_snapshots import append_nominal_snapshot

# --- LAYER 2 ANALYTIC INFRASTRUCTURE IMPORTS ---
try:
    import pandas as pd
    from analytic_engine.datasets import ComplianceMultiModalDataset
    from analytic_engine.graph_fusion import KnowledgeTriple, StructuralResolutionPayload, TemporalGraphFusionEngine
    from analytic_engine.models import BaseSurvivalModel
    from analytic_engine.router import CostAwareCascadingRouter
    from analytic_engine.time_series import InternalTelemetryEngine

    _LAYER2_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - optional Layer 2 deps may be absent for Layer 1 tests
    pd = Any  # type: ignore[assignment]
    ComplianceMultiModalDataset = None  # type: ignore[assignment]
    KnowledgeTriple = None  # type: ignore[assignment]
    StructuralResolutionPayload = None  # type: ignore[assignment]
    TemporalGraphFusionEngine = None  # type: ignore[assignment]
    BaseSurvivalModel = None  # type: ignore[assignment]
    CostAwareCascadingRouter = None  # type: ignore[assignment]
    InternalTelemetryEngine = None  # type: ignore[assignment]
    _LAYER2_IMPORT_ERROR = exc

DEFAULT_REPLAY_DIR = Path("data/layer1_replay")
DEFAULT_VAE_SNAPSHOT_DIR = Path("data/layer1_vae_snapshots")
DEFAULT_AUDIT_LOG_DIR = Path("data/layer1_audit_logs")
LIVE_NEWS_QUERY_COST_UNITS = 1.0
MOCK_NEWS_QUERY_COST_UNITS = 0.0


# --- LAYER 2 MULTI-MODAL PIPELINE ORCHESTRATOR ---
async def execute_hydra_pipeline(drift_event: dict[str, Any], transaction_history: pd.DataFrame):
    """
    Main Event-Driven Loop B Orchestrator.
    Consumes the stable Loop A 'DRIFT_EVENT' contract payload natively.
    """
    if _LAYER2_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Layer 2 optional dependencies are unavailable; Layer 1 can still run normally."
        ) from _LAYER2_IMPORT_ERROR

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


# --- LAYER 1 INFRASTRUCTURE WITH SNAPSHOT & LOCAL AUDIT ARCHIVING ---
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
    expand_adverse_news: bool = False,
    vae_snapshot_dir: str | Path | None = None,
    audit_log_dir: str | Path | None = None,
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
    drift_engine = KeywordDriftEngine(vae_snapshot_dir=vae_snapshot_dir)

    events = []
    dropped_signals = []
    for signal in signals:
        event = drift_engine.score_signal(baseline, signal)
        if event:
            event_payload = model_to_json_dict(event)
            events.append(event_payload)
            append_layer1_audit_record(
                audit_log_dir=audit_log_dir,
                client_id=baseline.client_id,
                record={
                    "decision": "accepted",
                    "event_id": event_payload["event_id"],
                    "severity": event_payload["severity"],
                    "drift_score": event_payload["drift_score"],
                    "routing_hint": event_payload["routing_hint"],
                    "title": event_payload["citations"][0].get("title", ""),
                    "source": signal.source,
                    "matched_risk_terms": event_payload["matched_risk_terms"],
                    "scoring_breakdown": event_payload["scoring_breakdown"],
                    "loop_a_trace": event_payload["loop_a_trace"],
                    "source_metadata": event_payload["source_metadata"],
                },
            )
        else:
            drop_reason = _drop_reason(baseline, signal)
            snapshot_saved = False
            if drop_reason == "stable_below_drift_threshold":
                snapshot_saved = append_nominal_snapshot(
                    client_id=baseline.client_id,
                    snapshot_dir=vae_snapshot_dir,
                    feature_vector=drift_engine.nominal_snapshot_for_signal(baseline, signal),
                    metadata={
                        "source": signal.source,
                        "signal_type": signal.signal_type.value
                        if hasattr(signal.signal_type, "value")
                        else str(signal.signal_type),
                        "title": str(signal.metadata.get("title", signal.content.splitlines()[0])),
                        "provider": str(signal.metadata.get("provider", "")),
                        "drop_reason": drop_reason,
                    },
                )
            dropped_signals.append(
                {
                    "client_id": signal.client_id,
                    "entity_name": signal.entity_name,
                    "signal_type": signal.signal_type.value
                    if hasattr(signal.signal_type, "value")
                    else str(signal.signal_type),
                    "source": signal.source,
                    "title": str(signal.metadata.get("title", signal.content.splitlines()[0])),
                    "drop_reason": drop_reason,
                    "vae_snapshot_saved": snapshot_saved,
                    "timestamp": signal.timestamp.isoformat(),
                }
            )
            append_layer1_audit_record(
                audit_log_dir=audit_log_dir,
                client_id=baseline.client_id,
                record={
                    "decision": "dropped",
                    "drop_reason": drop_reason,
                    "vae_snapshot_saved": snapshot_saved,
                    "title": str(signal.metadata.get("title", signal.content.splitlines()[0])),
                    "source": signal.source,
                    "signal_type": signal.signal_type.value
                    if hasattr(signal.signal_type, "value")
                    else str(signal.signal_type),
                    "timestamp": signal.timestamp.isoformat(),
                    "relevance_gate": evaluate_relevance(baseline, signal).__dict__,
                },
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
        "--vae-snapshot-dir",
        default=str(DEFAULT_VAE_SNAPSHOT_DIR),
        help="Directory for stable feature snapshots used by the lightweight VAE time-series buffer.",
    )
    parser.add_argument(
        "--audit-log-dir",
        default=str(DEFAULT_AUDIT_LOG_DIR),
        help="Directory for Layer 1 accepted/dropped signal audit logs.",
    )
    parser.add_argument(
        "--write-replay-dir",
        nargs="?",
        const=str(DEFAULT_REPLAY_DIR),
        help="Write raw_signals.jsonl, drift_events.jsonl, and dropped_signals.jsonl.",
    )
    parser.add_argument(
        "--run-layer2",
        action="store_true",
        help="Optionally cascade emitted DRIFT_EVENTs into the Layer 2 demo pipeline.",
    )
    args = parser.parse_args()

    # 1. Execute upstream Layer 1 data ingestion with baseline snapshotting and audit logging
    payload = run_layer1_pipeline(
        client_id=args.client_id,
        limit=args.limit,
        live=args.live,
        replay_file=args.replay_file,
        expand_adverse_news=args.expand_adverse_news,
        vae_snapshot_dir=args.vae_snapshot_dir,
        audit_log_dir=args.audit_log_dir,
    )

    if args.write_replay_dir:
        _write_replay_outputs(args.write_replay_dir, payload)

    # Print tracking metrics as expected by frontend hooks
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

    if not args.run_layer2:
        return

    # 2. Feed emitted Layer 1 drift events directly into Layer 2 Deep Analytics
    drift_events = payload["drift_events"]

    if not drift_events:
        print("\n✅ Layer 1 Scan Complete: No profile anomalies crossed threshold boundaries.")
        return

    # Build transaction time-series history dataframe mapping to volume metrics
    dates = pd.date_range(start="2026-05-01", end="2026-06-20", freq="D")
    volumes = [150 if i < (len(dates) - 1) else 2500000 for i in range(len(dates))]
    history_df = pd.DataFrame({"timestamp": dates, "value": volumes})

    # Sequentially cascade high-risk events through the active multi-modal survival loops
    for event in drift_events:
        asyncio.run(execute_hydra_pipeline(event, history_df))


if __name__ == "__main__":
    main()
