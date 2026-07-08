"""
Tiny connectivity smoke test for HYDRA's optional live integrations:
  1. Event Registry News API   (EVENT_REGISTRY_API_KEY)
  2. Nixtla TimeGPT            (NIXTLA_API_KEY)
  3. Apertus AI / PublicAI     (APERTUS_API_KEY)

This script only imports and calls the existing app classes/functions
exactly as they already run in the app - it does not edit any application
code.

Rules honoured:
  - Never prints or stores any API key value (only presence/absence is
    checked; any exception text is redacted before printing, as a
    defense-in-depth measure).
  - Requests are kept as small as possible.
  - Output is PASS / FAIL / SKIP plus the error type/message only.

NOTE ON COST: if APERTUS_API_KEY and/or NIXTLA_API_KEY are configured, this
script deliberately triggers one small real request to each service to
prove reachability (Apertus: ~$0.00015 per the router's own cost comment;
TimeGPT: one small anomaly-detection call on a 40-point series). Event
Registry: one tiny single-article query. To skip a given test, unset its
env var before running.

Usage:
    python tools/test_live_integrations.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RESULTS: list[tuple[str, str, str]] = []  # (name, status, detail)


def _redact(text: str, secret: str | None) -> str:
    """Strip the raw key value out of any text before it is printed."""
    if secret:
        text = text.replace(secret, "***REDACTED***")
    return text


def _record(name: str, status: str, detail: str = "") -> None:
    RESULTS.append((name, status, detail))
    line = f"[{status}] {name}"
    if detail:
        line += f" - {detail}"
    print(line)


def test_event_registry() -> None:
    name = "Event Registry (backend/collectors/news.py)"
    key = os.getenv("EVENT_REGISTRY_API_KEY")
    if not key:
        _record(name, "SKIP", "EVENT_REGISTRY_API_KEY not set")
        return

    try:
        from backend.collectors.news import EventRegistryNewsCollector

        collector = EventRegistryNewsCollector(expand_adverse_queries=False)
        collector.fetch_company_news("connectivity-test", "Apple", limit=1, days_back=1)
        if collector.last_query_count > 0:
            _record(name, "PASS", "live request completed")
        else:
            _record(name, "FAIL", "request did not complete (see [EventRegistry] log above)")
    except Exception as exc:
        _record(name, "FAIL", _redact(f"{type(exc).__name__}: {exc}", key))


def test_timegpt() -> None:
    name = "Nixtla TimeGPT (analytic_engine/time_series.py)"
    key = os.getenv("NIXTLA_API_KEY")
    if not key or key == "your_actual_timegpt_key_here":
        _record(name, "SKIP", "NIXTLA_API_KEY not set")
        return

    try:
        import pandas as pd
        from analytic_engine.time_series import InternalTelemetryEngine

        dates = pd.date_range(start="2026-01-01", periods=40, freq="D")
        values = [100 + (i % 5) - 2 for i in range(len(dates))]
        tiny_df = pd.DataFrame({"timestamp": dates, "value": values})

        engine = InternalTelemetryEngine()
        _, metrics = engine.detect_volumetric_anomaly(tiny_df)
        status = metrics.get("engine_status")
        if status == "production_live_nixtla":
            _record(name, "PASS", "live TimeGPT call completed")
        else:
            _record(name, "FAIL", f"engine_status={status} (live call failed, fell back)")
    except Exception as exc:
        _record(name, "FAIL", _redact(f"{type(exc).__name__}: {exc}", key))


def test_apertus() -> None:
    name = "Apertus AI / PublicAI (analytic_engine/router.py)"
    key = os.getenv("APERTUS_API_KEY")
    if not key:
        _record(name, "SKIP", "APERTUS_API_KEY not set")
        return

    try:
        from analytic_engine.router import CostAwareCascadingRouter

        router = CostAwareCascadingRouter()
        if router.client is None:
            _record(name, "FAIL", "client failed to initialize (see log above)")
            return

        # predicted_t < 7.0 forces the heavy (paid) path so this actually
        # reaches Apertus instead of taking the free LOW_RISK short-circuit.
        audit_log = router.evaluate_routing_tier(
            client_id="connectivity-test",
            predicted_t=0.5,
            raw_payload="Connectivity test payload.",
        )
        if audit_log.chain_of_thought.startswith("[LOCAL FALLBACK"):
            _record(name, "FAIL", "live call failed, fell back to local fallback reasoning")
        else:
            _record(name, "PASS", "live Apertus call completed")
    except Exception as exc:
        _record(name, "FAIL", _redact(f"{type(exc).__name__}: {exc}", key))


def main() -> int:
    print("HYDRA live integration connectivity check")
    print("=" * 50)
    test_event_registry()
    test_timegpt()
    test_apertus()
    print("=" * 50)

    failures = [r for r in RESULTS if r[1] == "FAIL"]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
