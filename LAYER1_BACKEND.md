# Layer 1 Backend Handoff

Layer 1 is the low-cost public intelligence gate. It converts raw public signals into
structured `DRIFT_EVENT` payloads for Layer 2.

## Current Workflow

1. Load simulated KYC baselines from `backend/kyc/profiles.json`.
2. Fetch company news through `backend/collectors/news.py`.
3. Emit shared `backend.models.RawSignal` objects.
4. Drop signals that fail the monitored-client relevance gate.
5. Score relevant signals with `stream_engine/drift_engine.py`.
6. Emit only meaningful `DRIFT_EVENT` objects.

Layer 1 does **not** run LLM reasoning, graph fusion, survival modeling, or final compliance decisions.

## Run Locally

```bash
python3 main.py --client-id demo-spacex-001 --limit 10
```

Write replay files without live API calls:

```bash
python3 main.py --client-id demo-spacex-001 --limit 10 --write-replay-dir data/layer1_replay
```

Replay cached raw signals:

```bash
python3 main.py --client-id demo-spacex-001 --replay-file data/layer1_replay/raw_signals.jsonl
```

Run Layer 1 unit tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Optional live news:

```bash
export EVENT_REGISTRY_API_KEY="..."
python3 main.py --client-id demo-spacex-001 --limit 10 --live --write-replay-dir data/layer1_replay
```

Optional adverse live query expansion:

```bash
export EVENT_REGISTRY_API_KEY="..."
python3 main.py --client-id demo-spacex-001 --limit 3 --live --expand-adverse-news --write-replay-dir data/layer1_replay_live_adverse
```

`--expand-adverse-news` runs the base company query plus adverse queries such as investigation, lawsuit, export control, governance, and offshore. Use small limits and replay files to control Event Registry cost.

## Contract for Layer 2

Layer 2 should consume the `drift_events` array from CLI output or `run_layer1()` in `main.py`.
Treat these fields as stable:

```json
{
  "schema_version": "layer1.drift_event.v1",
  "event_type": "DRIFT_EVENT",
  "event_id": "drift_...",
  "client_id": "demo-spacex-001",
  "client_name": "SpaceX",
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
    "relevance_score": 1.0,
    "adverse_sentiment_score": 0.084,
    "dense_semantic_shift_score": 0.61,
    "hybrid_shift_score": 0.68,
    "heuristic_score": 0.84,
    "reconstruction_error": 0.9,
    "dynamic_threshold": 0.35,
    "source_recency_score": 0.0,
    "source_reliability_score": 0.0
  },
  "loop_a_trace": {
    "trace_mode": "vae_compatible_proxy",
    "reconstruction_engine": "vae_compatible_statistical_proxy",
    "vae_reconstruction_error": 0.9,
    "drift_threshold": 0.35,
    "dynamic_variance": 0.0036,
    "drift_score": 0.9,
    "drift_detected": true,
    "relevance_gate": {
      "relevant": true,
      "score": 1.0,
      "matched_terms": ["SpaceX", "Elon Musk"],
      "reason": "matched_monitored_entity"
    },
    "top_keywords_matched": ["crypto exchange", "offshore"],
    "embedding_shift_score": 0.3,
    "decision": "DRIFT_EVENT emitted",
    "tokens_used": 0,
    "cost_usd": 0.0,
    "nominal_profile": {
      "fit_mode": "baseline_profile_proxy",
      "expected_signal_count": 9,
      "nominal_mean": 0.14,
      "nominal_std": 0.06
    },
    "sparse_encoder": {
      "encoder": "local_exact_activation",
      "activation_count": 8,
      "matched_entities": ["SpaceX", "Elon Musk"],
      "activations": {
        "risk::offshore": 1.0,
        "entity::SpaceX": 1.0
      }
    },
    "dense_encoder": {
      "encoder": "local_hashing_embedding",
      "dimensions": 32,
      "baseline_similarity": 0.39,
      "semantic_shift_score": 0.61,
      "signal_norm": 1.0,
      "baseline_norm": 1.0
    },
    "hybrid_encoder": {
      "encoder": "local_sparse_dense_hybrid",
      "sparse_dimensions": 8,
      "dense_dimensions": 32,
      "hybrid_dimensions": 40,
      "sparse_activation_ratio": 0.8,
      "semantic_shift_score": 0.61,
      "hybrid_shift_score": 0.68,
      "feature_families": ["risk_terms", "baseline_terms", "entities", "semantic_hash"]
    }
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
    "entity_name": "SpaceX",
    "sentiment_score": -0.7,
    "relevance_matched_terms": ["SpaceX", "Elon Musk"],
    "related_entities": ["Elon Musk", "Orbital Ventures Ltd"],
    "relationship_hints": ["partnership", "regulatory_investigation", "offshore_link"],
    "entity_roles": {
      "SpaceX": "monitored_client",
      "Elon Musk": "beneficial_owner_or_key_person",
      "Orbital Ventures Ltd": "partner_or_counterparty"
    }
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
  "client_id": "demo-spacex-001",
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

## Current MVP Coverage

- **Live news ingestion:** Event Registry API works with opt-in `--live`; adverse query expansion is opt-in via `--expand-adverse-news`.
- **Cost control:** default mode is mock/replay, live raw signals can be saved to JSONL, and replay runs use `news_queries: 0`.
- **Loop A gate:** relevance filtering, sparse/dense/hybrid local features, VAE-compatible reconstruction proxy, dynamic threshold, and stable-signal drop are implemented.
- **Layer 2 contract:** emitted `DRIFT_EVENT` payloads include citations, scoring breakdown, `loop_a_trace`, relationship hints, and stable schema fields.
- **Quality controls:** URL/title dedupe runs before scoring for live and replay article signals; unit tests cover mock, replay, relevance, dedupe, schema, and scoring.

## Notes for Layer 2

- `severity` is derived from `drift_score`: `medium`, `high`, or `critical`.
- `routing_hint` is advisory only; Layer 2 can still override routing.
- `relevance_gate` prevents unrelated public signals from reaching Layer 2 even if they contain generic risk terms.
- `loop_a_trace` is currently a VAE-compatible proxy; the interface can be swapped for a real VAE without changing Layer 2’s contract.
- `source_metadata.related_entities`, `relationship_hints`, and `entity_roles` are lightweight hints for Layer 2 GraphRAG.
- `citations` are the audit trail Layer 2 should preserve in any final explanation.
- Layer 1 does not use LLM tokens or heavy reasoner calls.

## Remaining TODO

### P0

1. **To check:** confirm whether the official “News MCP” is a separate MCP server/tool or whether the provided Event Registry API key counts as the News MCP/news-source integration. If Event Registry API is accepted, Layer 1 P0 is complete.

### P1

1. Replace proxy sparse features with SPLADE-style sparse encoding while keeping the existing `loop_a_trace.sparse_encoder` contract.
2. Replace local hashing dense features with a local ONNX transformer or approved free local model while keeping the existing `loop_a_trace.dense_encoder` contract.
3. Replace the VAE-compatible statistical proxy with a fitted lightweight VAE and learned dynamic threshold.
4. Add a streaming/scheduler loop with bounded queue/backpressure so Loop A can be described as high-throughput instead of one-shot CLI only.

### P2

1. Add a small latency/throughput benchmark for Loop A filtering.
2. Add source recency, source reliability, and signal type scoring.
3. Add full audit logging for accepted and dropped signals beyond the current CLI/replay drop reasons.
4. Move high-risk terms into config so risk teammates can tune them without editing client profiles.
5. Add basic data-safety guardrails to avoid leaking unnecessary internal baseline details downstream.
6. Add multi-client runner only if the demo needs portfolio-level monitoring.
