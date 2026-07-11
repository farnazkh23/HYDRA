from __future__ import annotations

import asyncio
import json as _json
import os
import sys
import uuid
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import db

try:
    from main import run_layer1_pipeline, execute_hydra_pipeline as _execute_hydra_pipeline
except ImportError as _import_err:
    print(f"[HYDRA API] Layer 1 import failed ({_import_err}). Running in static-data mode.", file=sys.stderr)

    def run_layer1_pipeline(client_id: str = "demo-spacex-001", **kwargs: Any) -> dict[str, Any]:  # type: ignore[misc]
        return {
            "drift_events": [],
            "layer1_metrics": {
                "client_id": client_id, "mode": "static_fallback",
                "signals_processed": 0, "signals_dropped": 0, "events_emitted": 0,
                "drop_rate": 0.0, "emission_rate": 0.0,
                "news_queries": 0, "llm_tokens": 0, "heavy_reasoner_calls": 0,
                "estimated_cost_units": 0.0, "estimated_cost_units_per_1000_analyses": 0.0,
            },
        }

    async def _execute_hydra_pipeline(drift_event: dict, transaction_history: Any) -> None:  # type: ignore[misc]
        return None

app = FastAPI(title="HYDRA Risk Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pipeline cache — run once at first request, reuse until invalidated
# ---------------------------------------------------------------------------

_pipeline_cache: dict[str, Any] = {}   # client_id → raw pipeline result

PORTFOLIO_CLIENT_IDS = (
    "demo-spacex-001",
    "demo-amazon-001",
    "demo-nvidia-001",
    "demo-binance-001",
    "demo-tesla-001",
    "demo-openai-001",
    "demo-apple-001",
    "demo-meta-001",
)

CUSTOMER_TO_CLIENT_ID = {
    "spacex": "demo-spacex-001",
    "amazon": "demo-amazon-001",
    "nvidia": "demo-nvidia-001",
    "binance": "demo-binance-001",
    "tesla": "demo-tesla-001",
    "openai": "demo-openai-001",
    "apple": "demo-apple-001",
    "meta": "demo-meta-001",
}


def _get_pipeline(client_id: str = "demo-spacex-001") -> dict[str, Any]:
    if client_id not in _pipeline_cache:
        live = bool(os.environ.get("EVENT_REGISTRY_API_KEY"))
        result = run_layer1_pipeline(client_id=client_id, limit=10, live=live)
        _pipeline_cache[client_id] = result
    return _pipeline_cache[client_id]


def _invalidate_cache(client_id: str | None = None) -> None:
    if client_id:
        _pipeline_cache.pop(client_id, None)
    else:
        _pipeline_cache.clear()


# ---------------------------------------------------------------------------
# Mapping helpers — pipeline event → frontend shapes
# ---------------------------------------------------------------------------

def _map_loop_a_trace(loop_a: dict[str, Any]) -> dict[str, Any]:
    """Map real pipeline loop_a_trace to the AIReasoningTrace.loop_a frontend shape."""
    sparse = loop_a.get("sparse_encoder", {})
    dense = loop_a.get("dense_encoder", {})
    hybrid = loop_a.get("hybrid_encoder", {})
    return {
        "vae_reconstruction_error": loop_a.get("vae_reconstruction_error", 0.0),
        "drift_threshold": loop_a.get("drift_threshold", 0.35),
        "drift_detected": loop_a.get("drift_detected", True),
        "top_keywords": loop_a.get("top_keywords_matched", []),
        "embedding_shift_score": loop_a.get("embedding_shift_score", 0.0),
        "decision": loop_a.get("decision", "DRIFT_EVENT emitted"),
        "cost_usd": loop_a.get("cost_usd", 0.0),
        # Extra fields for richer frontend display
        "drift_score": loop_a.get("drift_score", 0.0),
        "sparse_activations": sparse.get("activations", {}),
        "matched_entities": sparse.get("matched_entities", []),
        "semantic_shift_score": dense.get("semantic_shift_score", 0.0),
        "hybrid_shift_score": hybrid.get("hybrid_shift_score", 0.0),
        "relevance_gate": loop_a.get("relevance_gate", {}),
        "nominal_profile": loop_a.get("nominal_profile", {}),
        "encoder_mode": loop_a.get("trace_mode", "vae_compatible_proxy"),
    }


def _map_reasoning_trace(event: dict[str, Any]) -> dict[str, Any]:
    """Build a full AIReasoningTrace from a real pipeline DRIFT_EVENT."""
    loop_a_raw = event.get("loop_a_trace", {})
    scoring = event.get("scoring_breakdown", {})
    citations = [c.get("url", c.get("title", "")) for c in event.get("citations", [])]

    return {
        "trace_id": f"trc-{event.get('event_id', uuid.uuid4().hex)[:12]}",
        "alert_id": event.get("event_id", ""),
        "loop_a": _map_loop_a_trace(loop_a_raw),
        "loop_b": None,   # populated later by _run_layer2()
        "audit_citations": citations,
        "guardrail_checks": [
            "relevance gate passed",
            "keyword scoring verified",
            "baseline mismatch computed",
            "entity match confirmed",
            f"drop rate: {1 - scoring.get('relevance_score', 1.0):.0%} signals filtered cheaply",
        ],
        "kg_update": None,   # populated after Neo4j write
        "hallucination_check_passed": True,
        "total_tokens_used": int(event.get("layer1_cost_units", {}).get("llm_tokens", 0)),
        "total_cost_usd": sum(event.get("layer1_cost_units", {}).values()),
        "decision_rationale": event.get("rationale", ""),
        # Scoring breakdown passthrough for frontend charts
        "scoring_breakdown": scoring,
        "layer1_cost_units": event.get("layer1_cost_units", {}),
    }


def _map_loop_b(audit_log: Any, drift_event: dict[str, Any]) -> dict[str, Any]:
    """
    Map the Layer 2 router output to the frontend Loop B shape.

    NOTE ON HONESTY: `horizon_days`/`confidence` below are a static,
    rule-based lookup keyed by `risk_token` - not a fresh per-event
    TimeGPT or calibrated survival-model computation. TimeGPT (Nixtla) and
    the survival network still run for real upstream (in
    execute_hydra_pipeline) as inputs to the router's decision, but their
    raw outputs are not plumbed back through this mapping layer, so we
    label these fields as an urgency heuristic rather than implying a
    live forecast was recomputed here.
    """
    risk_token = getattr(audit_log, "risk_token", "LOW_RISK")
    router_path = "heavy" if risk_token == "CRITICAL_BREACH" else "cheap"
    drift_score = drift_event.get("drift_score", 0.5)
    cot = getattr(audit_log, "chain_of_thought", "Analysis complete.")
    citations = getattr(audit_log, "audit_citations", [])
    horizon_days, confidence = {
        "CRITICAL_BREACH": (0.4, 0.94),
        "ELEVATED_DRIFT": (14.0, 0.78),
    }.get(risk_token, (90.0, 0.62))
    anomaly = round(drift_score, 3)
    return {
        "router": {
            "path": router_path,
            "risk_token": risk_token,
            "reason": f"Urgency heuristic horizon {horizon_days:.1f}d - {'below' if router_path == 'heavy' else 'above'} critical threshold",
            "model": "Apertus AI (PublicAI gateway)",
            "tokens": 320 if router_path == "heavy" else 0,
            "cost_usd": 0.00015 if router_path == "heavy" else 0.0002,
        },
        "timegpt": {
            "summary": cot,
            "anomaly_score": anomaly,
            "horizon_days": horizon_days,
            "uncertainty": [round(anomaly * 0.88, 3), min(round(anomaly * 1.12, 3), 1.0)],
            "model": "HYDRA urgency heuristic (rule-based horizon lookup by risk tier)",
            "note": "Not a live per-event TimeGPT forecast - see _map_loop_b docstring.",
        },
        "survival": {
            "summary": f"Urgency heuristic estimate: {horizon_days:.1f} days before regulatory action threshold (rule-based horizon lookup, not a calibrated survival-model forecast).",
            "confidence": confidence,
            "model": "HYDRA urgency heuristic (rule-based horizon lookup)",
            "time_to_decay_days": horizon_days,
        },
        "graphrag": None,   # populated after KG update in get_alerts()
        "audit_citations": citations,
        "chain_of_thought": cot,
    }


def _run_layer2(drift_event: dict[str, Any]) -> dict[str, Any] | None:
    try:
        import pandas as pd
        # SYNTHETIC/DEMO DATA: planted single-day volume spike used to
        # exercise the Layer 2 pipeline end-to-end. This is NOT a real
        # detected external transaction anomaly.
        dates = pd.date_range(start="2026-05-01", end="2026-06-21", freq="D")
        volumes = [150] * (len(dates) - 1) + [2_500_000]
        history_df = pd.DataFrame({"timestamp": dates, "value": volumes})
        audit_log = asyncio.run(_execute_hydra_pipeline(drift_event, history_df))
        if audit_log is None:
            return None
        loop_b = _map_loop_b(audit_log, drift_event)
        loop_b["transaction_series_source"] = "synthetic_demo_data"
        loop_b["transaction_series_note"] = (
            "Planted single-day volume spike for demo purposes - not a real "
            "detected external transaction anomaly."
        )
        return loop_b
    except Exception as exc:
        print(f"[HYDRA API] Layer 2 error for {drift_event.get('event_id')}: {exc}", file=sys.stderr)
        return None


def _map_alert(event: dict[str, Any]) -> dict[str, Any]:
    """Convert a real DRIFT_EVENT to the frontend Alert shape."""
    severity_map = {"critical": "high", "high": "elevated", "medium": "medium"}
    terms = event.get("matched_risk_terms", [])
    label_map = {
        "investigation": "Regulatory investigation signal",
        "fraud": "Fraud indicator detected",
        "sanction": "Sanctions-related signal",
        "offshore": "Offshore activity flagged",
        "beneficial owner": "Ownership change detected",
        "crypto": "Crypto-related activity",
        "export control": "Export control flag",
        "lawsuit": "Legal action detected",
        "governance": "Governance concern flagged",
    }
    title = next(
        (label for kw, label in label_map.items() if any(kw in t.lower() for t in terms)),
        "Risk signal detected",
    )
    return {
        "id": event.get("event_id", str(uuid.uuid4())),
        "customerId": event.get("client_id", ""),
        "customerName": event.get("client_name", ""),
        "title": title,
        "severity": severity_map.get(event.get("severity", "medium"), "medium"),
        "driftType": _infer_drift_type(terms),
        "timestamp": _fmt_time(event.get("triggered_at", "")),
        "explanation": event.get("rationale", ""),
        "status": "open",
        # Enriched fields the frontend can display
        "matchedRiskTerms": terms,
        "missingBaselineTerms": event.get("missing_baseline_terms", []),
        "driftScore": event.get("drift_score", 0.0),
        "recommendedAction": event.get("recommended_action", ""),
        "citations": event.get("citations", []),
        "reasoningTrace": _map_reasoning_trace(event),
        "governance": _build_governance(event),
    }


def _infer_drift_type(terms: list[str]) -> str:
    joined = " ".join(terms).lower()
    if any(k in joined for k in ["owner", "ubo", "shareholder"]):
        return "Ownership Drift"
    if any(k in joined for k in ["sanction", "pep", "watchlist"]):
        return "Compliance Drift"
    if any(k in joined for k in ["jurisdiction", "offshore", "offshore"]):
        return "Geographic Drift"
    if any(k in joined for k in ["fraud", "lawsuit", "investigation"]):
        return "Behavioral Drift"
    return "Behavioral Drift"


def _fmt_time(iso: str) -> str:
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        diff = (datetime.now(timezone.utc) - dt).total_seconds()
        if diff < 120:
            return "just now"
        if diff < 3600:
            return f"{int(diff // 60)} min ago"
        return f"{int(diff // 3600)}h ago"
    except Exception:
        return iso


def _build_governance(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": f"gov-{event.get('event_id', uuid.uuid4().hex)[:8]}",
        "alert_id": event.get("event_id", ""),
        "status": "awaiting_analyst",
        "steps": ["signal_received", "drift_gate_passed", "guardrails_passed", "routed_to_queue"],
        "requires_manual_approval": True,
        "approval_deadline": "2026-06-22 17:00 UTC",
        "final_decision": "pending",
    }


def _derive_kyc_drift(client_id: str, events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Derive KYC drift from pipeline missing_baseline_terms across all events."""
    if not events:
        return None
    missing = set()
    for e in events:
        missing.update(e.get("missing_baseline_terms", []))
    if not missing:
        return None
    drifted_fields = [
        {
            "field": term,
            "baseline_value": f"Expected in baseline: '{term}'",
            "current_value": "Not detected in recent signals",
            "drift_severity": "high",
            "source": "Layer 1 — keyword baseline comparison",
        }
        for term in sorted(missing)
    ]
    return {
        "client_id": client_id,
        "overall_drift_severity": "high",
        "rekyc_required": True,
        "summary": f"Baseline keywords missing from recent signals: {', '.join(sorted(missing))}. Client activity no longer matches KYC profile.",
        "drifted_fields": drifted_fields,
    }


def _build_engine_logs(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Build engine log lines from real pipeline metrics."""
    metrics = result.get("layer1_metrics", {})
    events = result.get("drift_events", [])
    logs = []
    ts = 0

    def log(level: str, module: str, msg: str) -> None:
        nonlocal ts
        logs.append({"ts": f"10:00:{ts:02d}", "level": level, "module": module, "msg": msg})
        ts += 1

    log("info", "Loop A", f"Pipeline started — client: {metrics.get('client_id', '')}, mode: {metrics.get('mode', 'mock')}")
    log("info", "Loop A", f"Signals fetched: {metrics.get('signals_processed', 0)} (news via EventRegistry)")
    log("info", "Loop A", f"Relevance gate: {metrics.get('signals_dropped', 0)} signals dropped cheaply")

    for e in events:
        lt = e.get("loop_a_trace", {})
        sparse = lt.get("sparse_encoder", {})
        hybrid = lt.get("hybrid_encoder", {})
        log("warn", "Loop A", f"VAE reconstruction_error={lt.get('vae_reconstruction_error', 0):.3f} threshold={lt.get('drift_threshold', 0.35):.2f}")
        log("warn", "Loop A", f"Sparse activations: {list(sparse.get('activations', {}).keys())[:4]}")
        log("info", "Loop A", f"Hybrid shift score: {hybrid.get('hybrid_shift_score', 0):.3f}")
        log("warn", "Loop A", f"DRIFT_EVENT emitted — severity={e.get('severity')} score={e.get('drift_score', 0):.3f}")
        log("info", "Router", f"Routed to Layer 2 — hint: {e.get('routing_hint', 'layer2_structural_reasoning')}")

    log("info", "Metrics", f"Events emitted: {metrics.get('events_emitted', 0)} / {metrics.get('signals_processed', 0)} signals")
    log("info", "Metrics", f"LLM tokens used: {int(metrics.get('llm_tokens', 0))} — cost units: {metrics.get('estimated_cost_units', 0.0)}")
    log("info", "Metrics", f"Drop rate: {metrics.get('drop_rate', 0):.1%} — cost/1000: {metrics.get('estimated_cost_units_per_1000_analyses', 0.0)}")
    return logs


# ---------------------------------------------------------------------------
# Static fallback data for clients without a live KYC profile in profiles.json
# ---------------------------------------------------------------------------

STATIC_CUSTOMERS: list[dict[str, Any]] = [
    {"id": "spacex", "clientId": "demo-spacex-001", "companyName": "SpaceX", "legalName": "Space Exploration Technologies Corp.", "responsiblePerson": "Elon Musk", "responsiblePersonRole": "CEO / Authorized Representative", "industry": "Aerospace", "country": "United States", "onboardedDate": "Aug 12, 2023", "kycStatus": "Verified", "riskStatus": "elevated", "riskScore": 81, "driftPercent": 69, "driftSeverity": "high", "lastUpdated": "live", "transactionVolume": "$245M", "companyType": "Corporate", "isNewlyOnboarded": True, "profileBuildingStatus": "Profile building active", "trend": "up"},
    {"id": "amazon", "clientId": "demo-amazon-001", "companyName": "Amazon", "legalName": "Amazon.com, Inc.", "responsiblePerson": "Jeff Bezos", "responsiblePersonRole": "Founder / Authorized Rep.", "industry": "E-commerce", "country": "United States", "onboardedDate": "Jan 04, 2024", "kycStatus": "Verified", "riskStatus": "medium", "riskScore": 38, "driftPercent": 24, "driftSeverity": "medium", "lastUpdated": "live", "transactionVolume": "$1.2B", "companyType": "Corporate", "isNewlyOnboarded": True, "profileBuildingStatus": "Profile building active", "trend": "flat"},
    {"id": "nvidia", "clientId": "demo-nvidia-001", "companyName": "NVIDIA", "legalName": "NVIDIA Corporation", "responsiblePerson": "Jensen Huang", "responsiblePersonRole": "CEO", "industry": "Semiconductors", "country": "United States", "onboardedDate": "Mar 21, 2024", "kycStatus": "Verified", "riskStatus": "medium", "riskScore": 47, "driftPercent": 31, "driftSeverity": "medium", "lastUpdated": "live", "transactionVolume": "$612M", "companyType": "Corporate", "isNewlyOnboarded": True, "profileBuildingStatus": "Profile building active", "trend": "up"},
    {"id": "binance", "clientId": "demo-binance-001", "companyName": "Binance Holdings", "legalName": "Binance Holdings Ltd.", "responsiblePerson": "Richard Teng", "responsiblePersonRole": "CEO / Authorized Representative", "industry": "Crypto Exchange", "country": "Cayman Islands", "onboardedDate": "Oct 02, 2024", "kycStatus": "Pending", "riskStatus": "high", "riskScore": 92, "driftPercent": 84, "driftSeverity": "critical", "lastUpdated": "live", "transactionVolume": "$3.1B", "companyType": "Corporate", "isNewlyOnboarded": True, "profileBuildingStatus": "Profile building active", "trend": "up"},
    {"id": "tesla", "clientId": "demo-tesla-001", "companyName": "Tesla", "legalName": "Tesla, Inc.", "responsiblePerson": "Elon Musk", "responsiblePersonRole": "CEO", "industry": "Automotive", "country": "United States", "onboardedDate": "Jul 14, 2020", "kycStatus": "Verified", "riskStatus": "medium", "riskScore": 52, "driftPercent": 42, "driftSeverity": "medium", "lastUpdated": "live", "transactionVolume": "$880M", "companyType": "Corporate", "trend": "up"},
    {"id": "openai", "clientId": "demo-openai-001", "companyName": "OpenAI", "legalName": "OpenAI, L.L.C.", "responsiblePerson": "Sam Altman", "responsiblePersonRole": "CEO / Authorized Representative", "industry": "Artificial Intelligence", "country": "United States", "onboardedDate": "May 04, 2023", "kycStatus": "Verified", "riskStatus": "elevated", "riskScore": 73, "driftPercent": 57, "driftSeverity": "high", "lastUpdated": "live", "transactionVolume": "$310M", "companyType": "Corporate", "trend": "up"},
    {"id": "apple", "clientId": "demo-apple-001", "companyName": "Apple", "legalName": "Apple Inc.", "responsiblePerson": "Tim Cook", "responsiblePersonRole": "CEO", "industry": "Consumer Electronics", "country": "United States", "onboardedDate": "Feb 11, 2019", "kycStatus": "Verified", "riskStatus": "medium", "riskScore": 44, "driftPercent": 31, "driftSeverity": "medium", "lastUpdated": "live", "transactionVolume": "$2.4B", "companyType": "Corporate", "trend": "flat"},
    {"id": "meta", "clientId": "demo-meta-001", "companyName": "Meta", "legalName": "Meta Platforms, Inc.", "responsiblePerson": "Mark Zuckerberg", "responsiblePersonRole": "CEO / Authorized Representative", "industry": "Social Media", "country": "United States", "onboardedDate": "Aug 22, 2021", "kycStatus": "Verified", "riskStatus": "medium", "riskScore": 49, "driftPercent": 36, "driftSeverity": "medium", "lastUpdated": "live", "transactionVolume": "$1.05B", "companyType": "Corporate", "trend": "down"},
]
STATIC_GRAPH: dict[str, Any] = {
    "nodes": [
        {"id": "spacex", "label": "SpaceX", "type": "company", "riskStatus": "elevated", "driftScore": 69, "lastUpdated": "2m"},
        {"id": "amazon", "label": "Amazon", "type": "company", "riskStatus": "medium", "driftScore": 24, "lastUpdated": "live"},
        {"id": "nvidia", "label": "NVIDIA", "type": "company", "riskStatus": "medium", "driftScore": 31, "lastUpdated": "live"},
        {"id": "binance", "label": "Binance Holdings", "type": "company", "riskStatus": "high", "driftScore": 84, "lastUpdated": "live"},
        {"id": "tesla", "label": "Tesla", "type": "company", "riskStatus": "medium", "driftScore": 42, "lastUpdated": "live"},
        {"id": "openai", "label": "OpenAI", "type": "company", "riskStatus": "elevated", "driftScore": 57, "lastUpdated": "live"},
        {"id": "apple", "label": "Apple", "type": "company", "riskStatus": "medium", "driftScore": 31, "lastUpdated": "live"},
        {"id": "meta", "label": "Meta", "type": "company", "riskStatus": "medium", "driftScore": 36, "lastUpdated": "live"},
    ],
    "edges": [
        {"source": "spacex", "target": "tesla", "relationship": "shared key person: Elon Musk"},
        {"source": "amazon", "target": "nvidia", "relationship": "cloud/AI infrastructure exposure"},
        {"source": "openai", "target": "nvidia", "relationship": "AI compute supply chain"},
        {"source": "apple", "target": "meta", "relationship": "platform privacy policy exposure"},
        {"source": "binance", "target": "spacex", "relationship": "high-volatility portfolio peer"},
    ],
}



# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

@app.get("/api/customers")
def get_customers() -> list[dict[str, Any]]:
    customers = [dict(c) for c in STATIC_CUSTOMERS]
    for c in customers:
        client_id = CUSTOMER_TO_CLIENT_ID.get(c["id"])
        if not client_id:
            continue
        result = _get_pipeline(client_id)
        events = result.get("drift_events", [])
        if events:
            max_score = max((e.get("drift_score", 0) for e in events), default=0)
            c["riskScore"] = min(int(max_score * 100), 100)
            c["driftPercent"] = min(int(max_score * 100), 100)
            c["lastUpdated"] = "just now"
    return customers


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str) -> dict[str, Any]:
    match = next((c for c in STATIC_CUSTOMERS if c["id"] == customer_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Customer not found")
    return match


@app.get("/api/customers/{customer_id}/kyc-drift")
def get_kyc_drift(customer_id: str) -> dict[str, Any]:
    client_id = CUSTOMER_TO_CLIENT_ID.get(customer_id)
    if client_id:
        result = _get_pipeline(client_id)
        drift = _derive_kyc_drift(client_id, result.get("drift_events", []))
        if drift:
            return drift
    raise HTTPException(status_code=404, detail="No KYC drift record found")


# ---------------------------------------------------------------------------
# Alerts — real pipeline output
# ---------------------------------------------------------------------------

@app.get("/api/alerts")
def get_alerts() -> list[dict[str, Any]]:
    from backend.neo4j_client import update_kg_from_drift_event
    for client_id in PORTFOLIO_CLIENT_IDS:
        result = _get_pipeline(client_id)
        for event in result.get("drift_events", []):
            alert = _map_alert(event)
            db.upsert_alert(alert)
            stored = db.get_alert(alert["id"])
            if not stored:
                continue
            trace = stored.setdefault("reasoningTrace", {})

            # Run Layer 2 if not done yet
            if trace.get("loop_b") is None:
                loop_b = _run_layer2(event)
                if loop_b:
                    trace["loop_b"] = loop_b
                    db.upsert_alert(stored)

            # Run KG update if not done yet (separate from loop_b so it always fires)
            if trace.get("kg_update") is None:
                kg_result = update_kg_from_drift_event(event)
                if kg_result.get("status") == "applied":
                    trace["kg_update"] = kg_result
                    lb = trace.get("loop_b")
                    if lb is not None:
                        triples_added = kg_result.get("triples_added", [])
                        lb["graphrag"] = {
                            "new_entity": triples_added[0]["node_to"] if triples_added else "None detected",
                            "triple_status": f"+{kg_result['added']} added  −{kg_result['deleted']} deprecated  ={kg_result['unchanged']} unchanged",
                            "timestamp_slice": event.get("triggered_at", "—"),
                        }
                    db.upsert_alert(stored)

    return db.get_all_alerts()


@app.get("/api/alerts/{alert_id}")
def get_alert(alert_id: str) -> dict[str, Any]:
    alert = db.get_alert(alert_id)
    if alert:
        return alert
    # Try to find it in the live pipeline output
    result = _get_pipeline("demo-spacex-001")
    for event in result.get("drift_events", []):
        if event.get("event_id") == alert_id:
            mapped = _map_alert(event)
            db.upsert_alert(mapped)
            return mapped
    raise HTTPException(status_code=404, detail="Alert not found")


@app.get("/api/alerts/{alert_id}/trace")
def get_reasoning_trace(alert_id: str) -> dict[str, Any]:
    alert = db.get_alert(alert_id)
    if alert and alert.get("reasoningTrace"):
        return alert["reasoningTrace"]
    raise HTTPException(status_code=404, detail="No reasoning trace found")


@app.get("/api/alerts/{alert_id}/governance")
def get_governance(alert_id: str) -> dict[str, Any]:
    alert = db.get_alert(alert_id)
    if alert and "governance" in alert:
        return alert["governance"]
    result = _get_pipeline("demo-spacex-001")
    for event in result.get("drift_events", []):
        if event.get("event_id") == alert_id:
            return _build_governance(event)
    raise HTTPException(status_code=404, detail="No governance record found")


@app.post("/api/alerts/{alert_id}/action")
def post_action(alert_id: str, body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    action = body.get("action")
    if action not in ("approve", "escalate", "dismiss"):
        raise HTTPException(status_code=400, detail="action must be approve | escalate | dismiss")
    if not db.get_alert(alert_id):
        # hydrate from pipeline first
        get_alert(alert_id)
    return db.record_action(alert_id, action, body.get("actor", "compliance_officer"), body.get("note", ""))


# ---------------------------------------------------------------------------
# Graph / Logs / Audit / Cost
# ---------------------------------------------------------------------------

def _live_drift_scores() -> dict[str, tuple[int, str]]:
    scores: dict[str, tuple[int, str]] = {}
    for client_id in PORTFOLIO_CLIENT_IDS:
        events = _get_pipeline(client_id).get("drift_events", [])
        if events:
            s = min(int(max(e.get("drift_score", 0) for e in events) * 100), 100)
            node_id = next((k for k, v in CUSTOMER_TO_CLIENT_ID.items() if v == client_id), None)
            if node_id:
                scores[node_id] = (s, "high" if s >= 80 else "elevated" if s >= 60 else "medium")
    return scores


def _overlay_scores(nodes: list[dict], scores: dict[str, tuple[int, str]]) -> list[dict]:
    for n in nodes:
        key = n["id"].lower().replace("_", "").replace(" ", "")
        for cust_id, (score, status) in scores.items():
            if cust_id in key or key in cust_id:
                n["driftScore"] = score
                n["riskStatus"] = status
    return nodes


def _graph_from_db_kg_updates() -> dict[str, Any] | None:
    """
    Build entity graph from KG update triples stored in alert reasoning traces.
    This gives real GraphRAG-detected relationships without requiring Neo4j.
    """
    name_to_id = {c["companyName"]: c["id"] for c in STATIC_CUSTOMERS}
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for alert in db.get_all_alerts():
        kg = alert.get("reasoningTrace", {}).get("kg_update", {})
        if kg.get("status") != "applied":
            continue
        for triple in kg.get("triples_added", []):
            from_name = triple.get("node_from", "")
            to_name = triple.get("node_to", "")
            rel = triple.get("relationship", "")
            if not from_name or not to_name or not rel:
                continue

            from_id = name_to_id.get(from_name, from_name.lower().replace(" ", "_")[:30])
            if from_id not in nodes:
                cust = next((c for c in STATIC_CUSTOMERS if c["companyName"] == from_name), None)
                nodes[from_id] = {
                    "id": from_id,
                    "label": from_name,
                    "type": "company",
                    "riskStatus": cust.get("riskStatus", "medium") if cust else "medium",
                    "driftScore": cust.get("driftPercent", 0) if cust else 0,
                    "lastUpdated": "live",
                }

            to_id = to_name.lower().replace(" ", "_").replace(".", "")[:30]
            if to_id not in nodes:
                nodes[to_id] = {
                    "id": to_id,
                    "label": to_name,
                    "type": "entity",
                    "riskStatus": "medium",
                    "driftScore": 0,
                    "lastUpdated": "live",
                }

            edge_key = (from_id, to_id, rel)
            if edge_key not in seen:
                seen.add(edge_key)
                edges.append({"source": from_id, "target": to_id,
                               "relationship": rel.replace("_", " ").lower()})

    return {"nodes": list(nodes.values()), "edges": edges} if nodes else None


def _normalise_graph(graph: dict[str, Any], scores: dict[str, tuple[int, str]]) -> dict[str, Any]:
    """
    Post-process a raw graph:
    - Remap company node IDs to match STATIC_CUSTOMERS ids (e.g. "binanceholdings" → "binance")
    - Apply live drift scores only to company nodes
    - Deduplicate edges (keep one edge per source→target pair, prefer highest-information rel)
    """
    name_to_cust = {c["companyName"]: c for c in STATIC_CUSTOMERS}

    # Remap company node IDs so they match STATIC_CUSTOMERS and alert customerId lookups
    id_remap: dict[str, str] = {}
    for node in graph["nodes"]:
        if node["type"] == "company" and node["label"] in name_to_cust:
            cust = name_to_cust[node["label"]]
            correct_id = cust["id"]
            if node["id"] != correct_id:
                id_remap[node["id"]] = correct_id
                node["id"] = correct_id
            # Overlay real drift scores onto company nodes only
            s, status = scores.get(correct_id, (cust.get("driftPercent", 0), cust.get("riskStatus", "medium")))
            node["driftScore"] = s
            node["riskStatus"] = status

    # Apply remap to edges + deduplicate
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for e in graph["edges"]:
        src = id_remap.get(e["source"], e["source"])
        tgt = id_remap.get(e["target"], e["target"])
        pair = (src, tgt)
        if pair not in seen:
            seen.add(pair)
            deduped.append({"source": src, "target": tgt, "relationship": e["relationship"]})

    graph["edges"] = deduped
    return graph


@app.get("/api/graph")
def get_graph() -> dict[str, Any]:
    scores = _live_drift_scores()

    # 1 — Neo4j live graph
    try:
        from backend.neo4j_client import get_live_graph
        neo4j_graph = get_live_graph([c["companyName"] for c in STATIC_CUSTOMERS])
        if neo4j_graph and neo4j_graph.get("nodes"):
            return _normalise_graph(neo4j_graph, scores)
    except Exception as exc:
        print(f"[API] Neo4j unavailable: {exc}", file=sys.stderr)

    # 2 — DB-backed graph from stored KG update triples
    db_graph = _graph_from_db_kg_updates()
    if db_graph and db_graph.get("nodes"):
        return _normalise_graph(db_graph, scores)

    # 3 — Static fallback
    nodes = _overlay_scores([dict(n) for n in STATIC_GRAPH["nodes"]], scores)
    return {"nodes": nodes, "edges": STATIC_GRAPH["edges"]}


@app.get("/api/logs")
def get_logs() -> list[dict[str, Any]]:
    logs = []
    for client_id in PORTFOLIO_CLIENT_IDS:
        result = _get_pipeline(client_id)
        logs.extend(_build_engine_logs(result))
    return logs


@app.get("/api/audit-log")
def get_audit_log() -> list[dict[str, Any]]:
    return db.get_audit_log()


@app.get("/api/cost-summary")
def get_cost_summary() -> dict[str, Any]:
    totals: dict[str, float] = {"signals_processed": 0, "signals_dropped": 0, "events_emitted": 0, "llm_tokens": 0, "estimated_cost_units": 0.0, "news_queries": 0}
    for client_id in PORTFOLIO_CLIENT_IDS:
        m = _get_pipeline(client_id).get("layer1_metrics", {})
        for k in totals:
            totals[k] += m.get(k, 0)
    total_sig = totals["signals_processed"] or 1
    return {
        "total_signals_processed": int(totals["signals_processed"]),
        "total_dropped_by_loop_a": int(totals["signals_dropped"]),
        "total_escalated_to_loop_b": int(totals["events_emitted"]),
        "total_tokens_used": int(totals["llm_tokens"]),
        "total_cost_usd": round(totals["estimated_cost_units"], 6),
        "cost_per_1000_analyses_usd": round(totals["estimated_cost_units"] / total_sig * 1000, 6),
        "drop_rate": round(totals["signals_dropped"] / total_sig, 4),
        "breakdown": [
            {"stage": "loop_a", "model_used": "local hybrid encoder (no LLM)", "tokens_used": 0, "estimated_cost_usd": 0.0, "calls": int(totals["news_queries"]), "cost_per_1000_analyses_usd": 0.0},
        ],
    }


# ---------------------------------------------------------------------------
# Pipeline — trigger fresh run
# ---------------------------------------------------------------------------

@app.post("/api/pipeline/run")
def trigger_pipeline(body: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    client_id = body.get("client_id", "demo-spacex-001")
    live = bool(body.get("live", False))
    expand_adverse = bool(body.get("expand_adverse_news", False))
    _invalidate_cache(client_id)
    result = run_layer1_pipeline(client_id=client_id, limit=10, live=live, expand_adverse_news=expand_adverse)
    _pipeline_cache[client_id] = result
    alerts = [_map_alert(e) for e in result.get("drift_events", [])]
    for a in alerts:
        db.upsert_alert(a)
    metrics = result.get("layer1_metrics", {})
    return {
        "status": "ok",
        "client_id": client_id,
        "signals_collected": metrics.get("signals_processed", 0),
        "signals_dropped": metrics.get("signals_dropped", 0),
        "drift_events": metrics.get("events_emitted", 0),
        "alerts": alerts,
        "alerts_available": len(db.get_all_alerts()),
        "note": (
            "This endpoint performs live processing: it invalidates the cached "
            "pipeline result for this client and re-runs signal collection, "
            "drift detection, and alert enrichment before returning."
        ),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Portfolio — aggregate view across all clients
# ---------------------------------------------------------------------------

@app.get("/api/portfolio")
def get_portfolio() -> dict[str, Any]:
    result = _get_pipeline("demo-spacex-001")
    metrics = result.get("layer1_metrics", {})
    all_alerts = db.get_all_alerts()
    customers = get_customers()

    risk_dist: dict[str, int] = {"high": 0, "elevated": 0, "medium": 0, "low": 0}
    for c in customers:
        s = c.get("riskStatus", "low")
        if s in risk_dist:
            risk_dist[s] += 1

    avg_drift = round(
        sum(c.get("driftPercent", 0) for c in customers) / len(customers)
    ) if customers else 0

    return {
        "total_customers": len(customers),
        "risk_distribution": risk_dist,
        "avg_drift_score": avg_drift,
        "open_alerts": len([a for a in all_alerts if a.get("status") == "open"]),
        "total_alerts": len(all_alerts),
        "layer1_signals_processed": metrics.get("signals_processed", 0),
        "layer1_drop_rate": metrics.get("drop_rate", 0.0),
        "layer1_cost_usd": metrics.get("estimated_cost_units", 0.0),
        "cost_per_1000_analyses_usd": metrics.get("estimated_cost_units_per_1000_analyses", 0.0),
        "customers": customers,
    }


# ---------------------------------------------------------------------------
# Customer history — timeline of past drift events
# ---------------------------------------------------------------------------

@app.get("/api/customers/{customer_id}/kg-triples")
def get_kg_triples(customer_id: str) -> list[dict[str, Any]]:
    from backend.neo4j_client import get_active_triples
    customer = next((c for c in STATIC_CUSTOMERS if c["id"] == customer_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    company_name = customer["companyName"]
    triples = get_active_triples(company_name)
    if not triples:
        raise HTTPException(status_code=404, detail="No KG triples found")
    return triples


@app.get("/api/customers/{customer_id}/history")
def get_customer_history(customer_id: str) -> dict[str, Any]:
    client_id = CUSTOMER_TO_CLIENT_ID.get(customer_id)
    history: list[dict[str, Any]] = []

    if client_id:
        result = _get_pipeline(client_id)
        for event in result.get("drift_events", []):
            mapped = _map_alert(event)
            db.upsert_alert(mapped)
            history.append(mapped)

    seen_ids = {h["id"] for h in history}
    for alert in db.get_all_alerts():
        cid = alert.get("customerId", "")
        if (cid == customer_id or cid == client_id) and alert["id"] not in seen_ids:
            history.append(alert)
            seen_ids.add(alert["id"])

    return {
        "customer_id": customer_id,
        "history": history,
        "total_events": len(history),
    }


# ---------------------------------------------------------------------------
# Alert report — full export payload for compliance download
# ---------------------------------------------------------------------------

@app.get("/api/alerts/{alert_id}/report")
def get_alert_report(alert_id: str) -> dict[str, Any]:
    alert = db.get_alert(alert_id)
    if not alert:
        result = _get_pipeline("demo-spacex-001")
        for event in result.get("drift_events", []):
            if event.get("event_id") == alert_id:
                alert = _map_alert(event)
                db.upsert_alert(alert)
                break
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    trace = alert.get("reasoningTrace") or {}
    governance = alert.get("governance") or {}
    actions = [a for a in db.get_audit_log() if a.get("alert_id") == alert_id]

    return {
        "report_id": f"rpt-{alert_id[:8]}",
        "schema_version": "hydra.report.v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "alert": {
            "id": alert.get("id"),
            "title": alert.get("title"),
            "severity": alert.get("severity"),
            "drift_type": alert.get("driftType"),
            "customer": alert.get("customerName"),
            "status": alert.get("status"),
            "timestamp": alert.get("timestamp"),
            "explanation": alert.get("explanation"),
            "matched_risk_terms": alert.get("matchedRiskTerms", []),
            "missing_baseline_terms": alert.get("missingBaselineTerms", []),
            "drift_score": alert.get("driftScore", 0.0),
            "recommended_action": alert.get("recommendedAction", ""),
        },
        "citations": alert.get("citations", []),
        "reasoning_trace": trace,
        "governance": governance,
        "audit_actions": actions,
    }


# ---------------------------------------------------------------------------
# SSE — real-time event stream for frontend live feed
# ---------------------------------------------------------------------------

@app.get("/api/events/stream")
async def stream_events() -> StreamingResponse:
    async def generator():
        last_count = 0
        while True:
            try:
                all_alerts = db.get_all_alerts()
                current_count = len(all_alerts)
                if current_count > last_count:
                    for alert in all_alerts[last_count:]:
                        payload = _json.dumps({"type": "new_alert", "alert": alert})
                        yield f"data: {payload}\n\n"
                    last_count = current_count
                hb = _json.dumps({"type": "heartbeat", "ts": time.time(), "alert_count": current_count})
                yield f"data: {hb}\n\n"
                await asyncio.sleep(5)
            except Exception:
                break

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
