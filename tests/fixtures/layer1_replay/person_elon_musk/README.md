# DETERMINISTIC REPLAY / DEMO FIXTURE — not live data

`raw_signals.jsonl` is a **committed, deterministic replay fixture** for the
`person_elon_musk` Layer 1 KYC baseline. It exists so the management demo
produces stable, repeatable results even without a live Event Registry API
key or network access — live news runs are non-deterministic (some runs
return drift alerts, some don't).

Every record is `RawSignal`-compatible JSON (one object per line) and is
public, news-style, synthetic demo content:

- `source` is `"demo_replay_fixture"` and `metadata.provider` is
  `"demo_replay_fixture"` (never `"event_registry"` or `"mock"`), so any
  alert citation generated from this data is clearly traceable back to this
  fixture, not to a real news provider.
- `metadata.fixture_label` is set on every record as an explicit,
  machine-readable marker.
- Content describes fictional/generic scenarios (e.g. a fictional
  counterparty, "Meridian Capital Partners") loosely themed around public,
  already-known facts (Elon Musk as Tesla CEO). It is not sourced from real
  articles and contains no private data and no secrets.

Contents (by design):

1. One stable/expected-activity signal — Tesla infrastructure expansion,
   positive sentiment, no risk keywords. Gets dropped as
   `stable_below_drift_threshold`.
2. Two adverse-governance signals (offshore/regulatory investigation;
   governance lawsuit) that trigger `KeywordDriftEngine` drift events.

Load it via `run_layer1_pipeline(client_id="person_elon_musk", live=False,
replay_file=<path to raw_signals.jsonl>)`. See
`tests/test_layer1_pipeline.py::Layer1PipelineTests::test_replay_fixture_person_elon_musk_produces_deterministic_demo_alerts`.
