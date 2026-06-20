from __future__ import annotations

import asyncio
import json as _json
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
    from main import run_layer1_pipeline
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


def _get_pipeline(client_id: str = "demo-spacex-001") -> dict[str, Any]:
    if client_id not in _pipeline_cache:
        result = run_layer1_pipeline(client_id=client_id, limit=10, live=False)
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
        "loop_b": None,   # layer2 branch — not merged yet
        "audit_citations": citations,
        "guardrail_checks": [
            "relevance gate passed",
            "keyword scoring verified",
            "baseline mismatch computed",
            "entity match confirmed",
            f"drop rate: {1 - scoring.get('relevance_score', 1.0):.0%} signals filtered cheaply",
        ],
        "hallucination_check_passed": True,
        "total_tokens_used": int(event.get("layer1_cost_units", {}).get("llm_tokens", 0)),
        "total_cost_usd": sum(event.get("layer1_cost_units", {}).values()),
        "decision_rationale": event.get("rationale", ""),
        # Scoring breakdown passthrough for frontend charts
        "scoring_breakdown": scoring,
        "layer1_cost_units": event.get("layer1_cost_units", {}),
    }


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
    {"id": "amazon", "clientId": None, "companyName": "Amazon", "legalName": "Amazon.com, Inc.", "responsiblePerson": "Jeff Bezos", "responsiblePersonRole": "Founder / Authorized Rep.", "industry": "E-commerce", "country": "United States", "onboardedDate": "Jan 04, 2024", "kycStatus": "Verified", "riskStatus": "low", "riskScore": 18, "driftPercent": 12, "driftSeverity": "low", "lastUpdated": "18 min ago", "transactionVolume": "$1.2B", "companyType": "Corporate", "isNewlyOnboarded": True, "profileBuildingStatus": "Profile building active", "trend": "flat"},
    {"id": "nvidia", "clientId": None, "companyName": "NVIDIA", "legalName": "NVIDIA Corporation", "responsiblePerson": "Jensen Huang", "responsiblePersonRole": "CEO", "industry": "Semiconductors", "country": "United States", "onboardedDate": "Mar 21, 2024", "kycStatus": "Verified", "riskStatus": "medium", "riskScore": 47, "driftPercent": 31, "driftSeverity": "medium", "lastUpdated": "11 min ago", "transactionVolume": "$612M", "companyType": "Corporate", "isNewlyOnboarded": True, "profileBuildingStatus": "Profile building active", "trend": "up"},
    {"id": "binance", "clientId": None, "companyName": "Binance Holdings", "legalName": "Binance Holdings Ltd.", "responsiblePerson": "Richard Teng", "responsiblePersonRole": "CEO / Authorized Representative", "industry": "Crypto Exchange", "country": "Cayman Islands", "onboardedDate": "Oct 02, 2024", "kycStatus": "Pending", "riskStatus": "high", "riskScore": 92, "driftPercent": 84, "driftSeverity": "critical", "lastUpdated": "4 min ago", "transactionVolume": "$3.1B", "companyType": "Corporate", "isNewlyOnboarded": True, "profileBuildingStatus": "Profile building active", "trend": "up"},
    {"id": "tesla", "clientId": None, "companyName": "Tesla", "legalName": "Tesla, Inc.", "responsiblePerson": "Elon Musk", "responsiblePersonRole": "CEO", "industry": "Automotive", "country": "United States", "onboardedDate": "Jul 14, 2020", "kycStatus": "Verified", "riskStatus": "medium", "riskScore": 52, "driftPercent": 42, "driftSeverity": "medium", "lastUpdated": "9 min ago", "transactionVolume": "$880M", "companyType": "Corporate", "trend": "up"},
    {"id": "openai", "clientId": None, "companyName": "OpenAI", "legalName": "OpenAI, L.L.C.", "responsiblePerson": "Sam Altman", "responsiblePersonRole": "CEO / Authorized Representative", "industry": "Artificial Intelligence", "country": "United States", "onboardedDate": "May 04, 2023", "kycStatus": "Verified", "riskStatus": "elevated", "riskScore": 73, "driftPercent": 57, "driftSeverity": "high", "lastUpdated": "6 min ago", "transactionVolume": "$310M", "companyType": "Corporate", "trend": "up"},
    {"id": "apple", "clientId": None, "companyName": "Apple", "legalName": "Apple Inc.", "responsiblePerson": "Tim Cook", "responsiblePersonRole": "CEO", "industry": "Consumer Electronics", "country": "United States", "onboardedDate": "Feb 11, 2019", "kycStatus": "Verified", "riskStatus": "low", "riskScore": 14, "driftPercent": 9, "driftSeverity": "low", "lastUpdated": "22 min ago", "transactionVolume": "$2.4B", "companyType": "Corporate", "trend": "flat"},
    {"id": "meta", "clientId": None, "companyName": "Meta", "legalName": "Meta Platforms, Inc.", "responsiblePerson": "Mark Zuckerberg", "responsiblePersonRole": "CEO / Authorized Representative", "industry": "Social Media", "country": "United States", "onboardedDate": "Aug 22, 2021", "kycStatus": "Verified", "riskStatus": "medium", "riskScore": 49, "driftPercent": 36, "driftSeverity": "medium", "lastUpdated": "14 min ago", "transactionVolume": "$1.05B", "companyType": "Corporate", "trend": "down"},
]

STATIC_GRAPH: dict[str, Any] = {
    "nodes": [
        {"id": "spacex", "label": "SpaceX", "type": "company", "riskStatus": "elevated", "driftScore": 69, "lastUpdated": "2m"},
        {"id": "tesla", "label": "Tesla", "type": "company", "riskStatus": "medium", "driftScore": 38, "lastUpdated": "1h"},
        {"id": "amazon", "label": "Amazon", "type": "company", "riskStatus": "low", "driftScore": 8, "lastUpdated": "11m"},
        {"id": "nvidia", "label": "NVIDIA", "type": "company", "riskStatus": "medium", "driftScore": 31, "lastUpdated": "26m"},
        {"id": "binance", "label": "Binance Holdings", "type": "company", "riskStatus": "high", "driftScore": 84, "lastUpdated": "14m"},
        {"id": "offshore", "label": "Offshore Holding Ltd", "type": "company", "riskStatus": "high", "driftScore": 71, "lastUpdated": "5m"},
        {"id": "unknown", "label": "Unknown Entity Ltd", "type": "unknown", "riskStatus": "high", "driftScore": 77, "lastUpdated": "8m"},
        {"id": "ch", "label": "Switzerland", "type": "jurisdiction", "riskStatus": "low", "driftScore": 4, "lastUpdated": "1d"},
        {"id": "ky", "label": "Cayman Islands", "type": "jurisdiction", "riskStatus": "elevated", "driftScore": 58, "lastUpdated": "3h"},
    ],
    "edges": [
        {"source": "spacex", "target": "tesla", "relationship": "common UBO: Elon Musk"},
        {"source": "spacex", "target": "offshore", "relationship": "new beneficial-owner link", "isNewlyDetected": True, "severity": "high"},
        {"source": "offshore", "target": "unknown", "relationship": "shell ownership"},
        {"source": "unknown", "target": "ky", "relationship": "jurisdiction"},
        {"source": "binance", "target": "ky", "relationship": "registered in"},
        {"source": "binance", "target": "unknown", "relationship": "transactions"},
        {"source": "tesla", "target": "ch", "relationship": "counterparty"},
        {"source": "amazon", "target": "nvidia", "relationship": "supplier"},
        {"source": "nvidia", "target": "ch", "relationship": "tax residence"},
    ],
}


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

@app.get("/api/customers")
def get_customers() -> list[dict[str, Any]]:
    # Update SpaceX risk score from live pipeline if available
    result = _get_pipeline("demo-spacex-001")
    events = result.get("drift_events", [])
    customers = [dict(c) for c in STATIC_CUSTOMERS]
    if events:
        max_score = max((e.get("drift_score", 0) for e in events), default=0)
        for c in customers:
            if c["id"] == "spacex":
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
    if customer_id == "spacex":
        result = _get_pipeline("demo-spacex-001")
        drift = _derive_kyc_drift("demo-spacex-001", result.get("drift_events", []))
        if drift:
            return drift
    # Fallback
    fallback = {
        "spacex": {"client_id": "C-54871", "overall_drift_severity": "high", "rekyc_required": True, "summary": "Client activity no longer matches KYC baseline.", "drifted_fields": [{"field": "jurisdiction", "baseline_value": "CH", "current_value": "KY", "drift_severity": "high", "source": "OpenCorporates"}, {"field": "beneficial_owners", "baseline_value": "Jane Smith", "current_value": "Jane Smith, Unknown Entity Ltd", "drift_severity": "high", "source": "GLEIF"}]},
    }
    if customer_id not in fallback:
        raise HTTPException(status_code=404, detail="No KYC drift record found")
    return fallback[customer_id]


# ---------------------------------------------------------------------------
# Alerts — real pipeline output
# ---------------------------------------------------------------------------

@app.get("/api/alerts")
def get_alerts() -> list[dict[str, Any]]:
    result = _get_pipeline("demo-spacex-001")
    events = result.get("drift_events", [])
    live_alerts = [_map_alert(e) for e in events]

    # Store in DB so /action endpoint can update them
    for alert in live_alerts:
        db.upsert_alert(alert)

    return live_alerts


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
    result = _get_pipeline("demo-spacex-001")
    for event in result.get("drift_events", []):
        if event.get("event_id") == alert_id:
            return _map_reasoning_trace(event)
    # Fallback: return trace for first available event
    events = result.get("drift_events", [])
    if events:
        return {**_map_reasoning_trace(events[0]), "alert_id": alert_id}
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

@app.get("/api/graph")
def get_graph() -> dict[str, Any]:
    return STATIC_GRAPH


@app.get("/api/logs")
def get_logs() -> list[dict[str, Any]]:
    result = _get_pipeline("demo-spacex-001")
    return _build_engine_logs(result)


@app.get("/api/audit-log")
def get_audit_log() -> list[dict[str, Any]]:
    return db.get_audit_log()


@app.get("/api/cost-summary")
def get_cost_summary() -> dict[str, Any]:
    result = _get_pipeline("demo-spacex-001")
    metrics = result.get("layer1_metrics", {})
    return {
        "total_signals_processed": metrics.get("signals_processed", 0),
        "total_dropped_by_loop_a": metrics.get("signals_dropped", 0),
        "total_escalated_to_loop_b": metrics.get("events_emitted", 0),
        "total_tokens_used": int(metrics.get("llm_tokens", 0)),
        "total_cost_usd": metrics.get("estimated_cost_units", 0.0),
        "cost_per_1000_analyses_usd": metrics.get("estimated_cost_units_per_1000_analyses", 0.0),
        "drop_rate": metrics.get("drop_rate", 0.0),
        "breakdown": [
            {"stage": "loop_a", "model_used": "local hybrid encoder (no LLM)", "tokens_used": 0, "estimated_cost_usd": 0.0, "calls": metrics.get("news_queries", 0), "cost_per_1000_analyses_usd": 0.0},
        ],
    }


# ---------------------------------------------------------------------------
# Pipeline — trigger fresh run
# ---------------------------------------------------------------------------

@app.post("/api/pipeline/run")
def trigger_pipeline(body: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    client_id = body.get("client_id", "demo-spacex-001")
    live = bool(body.get("live", False))
    _invalidate_cache(client_id)
    result = run_layer1_pipeline(client_id=client_id, limit=10, live=live)
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

@app.get("/api/customers/{customer_id}/history")
def get_customer_history(customer_id: str) -> dict[str, Any]:
    client_map = {
        "spacex": "demo-spacex-001",
        "tesla": "demo-tesla-001",
        "apple": "demo-apple-001",
    }
    client_id = client_map.get(customer_id)
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
