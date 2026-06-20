# Layer 1 Backend Handoff

Layer 1 is the low-cost public intelligence gate. It converts raw public signals into
structured `DRIFT_EVENT` payloads for Layer 2.

## Current Workflow

1. Load simulated KYC baselines from `backend/kyc/profiles.json`.
2. Fetch company news through `backend/collectors/news.py`.
3. Emit shared `backend.models.RawSignal` objects.
4. Score each signal with `stream_engine/drift_engine.py`.
5. Emit only meaningful `DRIFT_EVENT` objects.

Layer 1 does **not** run LLM reasoning, graph fusion, survival modeling, or final compliance decisions.

## Run Locally

```bash
python3 main.py --client-id demo-aminaclient-001 --limit 10
```

Write replay files without live API calls:

```bash
python3 main.py --client-id demo-aminaclient-001 --limit 10 --write-replay-dir data/layer1_replay
```

Replay cached raw signals:

```bash
python3 main.py --client-id demo-aminaclient-001 --replay-file data/layer1_replay/raw_signals.jsonl
```

Run Layer 1 unit tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Optional live news:

```bash
export EVENT_REGISTRY_API_KEY="..."
python3 main.py --client-id demo-aminaclient-001 --limit 10 --live --write-replay-dir data/layer1_replay
```

## Contract for Layer 2

Layer 2 should consume the `drift_events` array from CLI output or `run_layer1()` in `main.py`.
Treat these fields as stable:

```json
{
  "schema_version": "layer1.drift_event.v1",
  "event_type": "DRIFT_EVENT",
  "event_id": "drift_...",
  "client_id": "demo-aminaclient-001",
  "client_name": "HelioPay AG",
  "routing_hint": "layer2_structural_reasoning",
  "severity": "high",
  "drift_score": 0.84,
  "triggered_at": "2026-06-19T20:58:57.086664+00:00",
  "matched_risk_terms": ["crypto exchange", "offshore"],
  "missing_baseline_terms": ["payments", "saas"],
  "scoring_breakdown": {
    "risk_term_score": 0.54,
    "baseline_mismatch_score": 0.2,
    "entity_match_score": 0.1,
    "source_recency_score": 0.0,
    "source_reliability_score": 0.0
  },
  "rationale": "Public signal deviates from baseline...",
  "recommended_action": "Trigger enhanced due diligence and route to Layer 2 structural reasoning.",
  "citations": [
    {
      "title": "Article title",
      "url": "https://...",
      "published_at": "2026-06-19T20:58:57.086518+00:00",
      "source": "event_registry"
    }
  ],
  "source_metadata": {
    "raw_signal_id": "sig_...",
    "signal_type": "news",
    "source": "event_registry",
    "provider": "event_registry",
    "entity_name": "HelioPay AG"
  },
  "layer1_cost_units": {
    "news_queries": 1.0,
    "llm_tokens": 0.0,
    "heavy_reasoner_calls": 0.0
  }
}
```

The CLI also emits `layer1_metrics` for frontend/cost tracking:

```json
{
  "schema_version": "layer1.metrics.v1",
  "client_id": "demo-aminaclient-001",
  "mode": "mock",
  "signals_processed": 3,
  "signals_dropped": 1,
  "events_emitted": 2,
  "drop_rate": 0.3333,
  "emission_rate": 0.6667,
  "news_queries": 1,
  "llm_tokens": 0,
  "heavy_reasoner_calls": 0,
  "estimated_cost_units": 0.0,
  "estimated_cost_units_per_1000_analyses": 0.0
}
```

## Notes for Layer 2

- `drift_score < 0.35` is dropped by Layer 1 and will not reach Layer 2.
- `severity` is derived from `drift_score`: `medium`, `high`, or `critical`.
- `routing_hint` is advisory only; Layer 2 can still override routing.
- `scoring_breakdown` is explainability metadata for the cheap Layer 1 gate.
- `citations` are the audit trail Layer 2 should preserve in any final explanation.
- `layer1_metrics` is for dashboards and judging; Layer 2 does not need it for reasoning.
- `layer1_cost_units.llm_tokens` is currently always `0.0` by design.
- Mock fallback is intentional so the demo still works without network/API access.
- Shared schemas now live in `backend/models.py`.
- Live API calls are opt-in via `--live`; default runs use mock or replay only.

## TODO-List

### P0

1. Replace/augment `backend/collectors/news.py` with the team’s News MCP integration while keeping mock fallback.
2. Add `schema_version`, `routing_hint`, `source_metadata`, and `scoring_breakdown` to `DriftEvent` without breaking existing fields. **Done.**
3. Add JSONL persistence/replay for `RawSignal`, emitted `DRIFT_EVENT`, and dropped stable signals. **Done for CLI/demo path.**
4. Add Layer 1 metrics: signals processed, signals dropped, events emitted, drop rate, news queries, and estimated cost per 1,000 analyses. **Done for CLI/demo path.**
5. Add unit tests for News MCP/mock fallback, scoring thresholds, dropped stable signals, and `DRIFT_EVENT` schema stability. **Done for current Layer 1 MVP.**
6. Add multi-client runner so Layer 1 can process every profile in `backend/kyc/profiles.json`, not only one CLI client.
7. Keep the existing `DRIFT_EVENT` output contract stable so Layer 2 does not need to change.

### P1

1. Improve the KYC baseline beyond keywords: business model, jurisdictions, expected activity, ownership assumptions, risk appetite, expected transaction profile, website/domain, and last KYC review.
2. Add at least one non-news public source adapter: sanctions/watchlists, registry/entity changes, domain/website changes, or funding/expansion signals.
3. Add explainable scoring components: risk terms, baseline mismatch, source recency, source reliability, entity match, adverse sentiment, and signal type.
4. Add audit logging for accepted and dropped signals, including drop reason and source citation.
5. Move thresholds and high-risk terms into config so compliance/risk teammates can tune them without editing code.
6. Add deduplication across articles/events by title, URL, entity, and time window before scoring.
7. Add basic data-safety guardrails: do not emit unnecessary internal baseline details, and keep public-signal data separate from simulated KYC data.

### P2(Optional)

1. Add sparse encoder path for exact high-risk keyword/entity activation, ideally SPLADE or a lightweight equivalent.
2. Add dense encoder path using a local ONNX transformer for semantic drift detection.
3. Combine sparse and dense features into one hybrid signal representation.
4. Train or fit a lightweight VAE on nominal baseline behavior.
5. Replace the current heuristic `drift_score` with VAE reconstruction loss plus dynamic variance thresholds.
6. Emit Loop A trace fields expected by `backend.models.LoopATrace`: reconstruction error, threshold, drift decision, matched keywords, embedding shift, tokens, and cost.
7. Add a streaming/scheduler loop with bounded queue/backpressure so Loop A can be described as high-throughput instead of one-shot CLI only.
