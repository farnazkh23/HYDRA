from __future__ import annotations

import tempfile
import unittest
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.collectors.news import mock_company_news
from backend.kyc.store import load_layer1_baselines
from backend.models import RawSignal, SignalType
from backend.replay import load_raw_signals, write_raw_signals
from main import _write_replay_outputs, run_layer1_pipeline
from stream_engine.drift_engine import KeywordDriftEngine


class Layer1PipelineTests(unittest.TestCase):
    @staticmethod
    def _write_mock_news_fixture(replay_dir: Path, client_id: str, legal_name: str) -> Path:
        """Explicit, on-disk replay fixture — not an implicit pipeline fallback."""
        replay_file = replay_dir / f"{client_id}-raw_signals.jsonl"
        write_raw_signals(replay_file, list(mock_company_news(client_id, legal_name)))
        return replay_file

    def test_mock_pipeline_without_fixtures_returns_empty_results(self) -> None:
        payload = run_layer1_pipeline(
            client_id="demo-spacex-001",
            limit=10,
            live=False,
        )

        self.assertEqual(payload["raw_signals"], [])
        self.assertEqual(payload["drift_events"], [])
        self.assertEqual(payload["dropped_signals"], [])
        self.assertEqual(payload["layer1_metrics"]["mode"], "mock")
        self.assertEqual(payload["layer1_metrics"]["signals_processed"], 0)
        self.assertEqual(payload["layer1_metrics"]["events_emitted"], 0)
        self.assertEqual(payload["layer1_metrics"]["signals_dropped"], 0)
        self.assertEqual(payload["layer1_metrics"]["drop_rate"], 0.0)
        self.assertEqual(payload["layer1_metrics"]["news_queries"], 0)

    def test_mock_pipeline_without_fixtures_returns_empty_for_all_personas(self) -> None:
        for client_id in [
            "demo-spacex-001",
            "demo-amazon-001",
            "demo-nvidia-001",
            "demo-binance-001",
            "demo-tesla-001",
            "demo-openai-001",
            "demo-apple-001",
            "demo-meta-001",
        ]:
            payload = run_layer1_pipeline(
                client_id=client_id,
                limit=10,
                live=False,
            )

            self.assertEqual(payload["layer1_metrics"]["client_id"], client_id)
            self.assertEqual(payload["raw_signals"], [])
            self.assertEqual(payload["drift_events"], [])

    def test_frontend_portfolio_personas_use_expected_key_people(self) -> None:
        expected_people = {
            "demo-amazon-001": "Jeff Bezos",
            "demo-nvidia-001": "Jensen Huang",
            "demo-binance-001": "Richard Teng",
            "demo-openai-001": "Sam Altman",
            "demo-apple-001": "Tim Cook",
            "demo-meta-001": "Mark Zuckerberg",
        }
        baselines = load_layer1_baselines()
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_dir = Path(temp_dir)
            for client_id, expected_person in expected_people.items():
                fixture_file = self._write_mock_news_fixture(
                    replay_dir, client_id, baselines[client_id].legal_name
                )

                payload = run_layer1_pipeline(
                    client_id=client_id,
                    limit=10,
                    live=False,
                    replay_file=str(fixture_file),
                )

                event_entities = [
                    entity
                    for event in payload["drift_events"]
                    for entity in event["source_metadata"]["related_entities"]
                ]
                self.assertIn(expected_person, event_entities)

    def test_audit_log_records_accepted_and_dropped_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_dir = Path(temp_dir)
            audit_dir = replay_dir / "audit"
            baseline = load_layer1_baselines()["demo-spacex-001"]
            fixture_file = self._write_mock_news_fixture(
                replay_dir, baseline.client_id, baseline.legal_name
            )
            payload = run_layer1_pipeline(
                client_id="demo-spacex-001",
                limit=10,
                live=False,
                replay_file=str(fixture_file),
                audit_log_dir=audit_dir,
            )
            self.assertGreater(len(payload["raw_signals"]), 0)
            audit_file = audit_dir / "demo-spacex-001.jsonl"
            records = [json.loads(line) for line in audit_file.read_text().splitlines()]

            self.assertEqual(len(records), len(payload["raw_signals"]))
            self.assertEqual(
                len([record for record in records if record["decision"] == "accepted"]),
                len(payload["drift_events"]),
            )
            self.assertEqual(
                len([record for record in records if record["decision"] == "dropped"]),
                len(payload["dropped_signals"]),
            )
            self.assertTrue(all(record["schema_version"] == "layer1.audit.v1" for record in records))

    def test_replay_round_trip_does_not_require_live_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_dir = Path(temp_dir)
            baseline = load_layer1_baselines()["demo-spacex-001"]
            fixture_file = self._write_mock_news_fixture(
                replay_dir, baseline.client_id, baseline.legal_name
            )

            original = run_layer1_pipeline(
                client_id="demo-spacex-001",
                limit=10,
                live=False,
                replay_file=str(fixture_file),
            )
            self.assertGreater(len(original["raw_signals"]), 0)
            _write_replay_outputs(replay_dir, original)

            self.assertEqual(
                len(load_raw_signals(replay_dir / "raw_signals.jsonl")),
                len(original["raw_signals"]),
            )
            self.assertEqual(
                (replay_dir / "drift_events.jsonl").read_text().count("\n"),
                len(original["drift_events"]),
            )
            self.assertEqual(
                (replay_dir / "dropped_signals.jsonl").read_text().count("\n"),
                len(original["dropped_signals"]),
            )
            self.assertEqual((replay_dir / "layer1_metrics.jsonl").read_text().count("\n"), 1)

            replayed = run_layer1_pipeline(
                client_id="demo-spacex-001",
                limit=10,
                live=False,
                replay_file=str(replay_dir / "raw_signals.jsonl"),
            )

            self.assertEqual(len(replayed["drift_events"]), len(original["drift_events"]))
            self.assertEqual(replayed["layer1_metrics"]["mode"], "replay")
            self.assertEqual(replayed["layer1_metrics"]["news_queries"], 0)
            self.assertTrue(
                all(
                    event["layer1_cost_units"]["news_queries"] == 0.0
                    for event in replayed["drift_events"]
                )
            )

    def test_stable_drops_feed_vae_snapshot_buffer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_dir = Path(temp_dir)
            snapshot_dir = replay_dir / "vae_snapshots"
            baseline = load_layer1_baselines()["demo-spacex-001"]
            fixture_file = self._write_mock_news_fixture(
                replay_dir, baseline.client_id, baseline.legal_name
            )

            first_run = run_layer1_pipeline(
                client_id="demo-spacex-001",
                limit=10,
                live=False,
                replay_file=str(fixture_file),
                vae_snapshot_dir=snapshot_dir,
            )

            self.assertEqual(len(first_run["dropped_signals"]), 1)
            self.assertTrue(first_run["dropped_signals"][0]["vae_snapshot_saved"])
            self.assertEqual((snapshot_dir / "demo-spacex-001.jsonl").read_text().count("\n"), 1)

            second_run = run_layer1_pipeline(
                client_id="demo-spacex-001",
                limit=10,
                live=False,
                replay_file=str(fixture_file),
                vae_snapshot_dir=snapshot_dir,
            )
            # nominal_profile only carries time_series_snapshots when the lightweight VAE
            # engine is available (see test_layer1_drift_engine.py for the same guard);
            # other engines fall back silently depending on optional numpy/sklearn install.
            snapshot_counts = [
                event["loop_a_trace"]["nominal_profile"]["time_series_snapshots"]
                for event in second_run["drift_events"]
                if event["loop_a_trace"]["reconstruction_engine"] == "lightweight_vae_reconstruction"
            ]

            self.assertTrue(all(count >= 1 for count in snapshot_counts))

    def test_replay_irrelevant_signal_has_specific_drop_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_dir = Path(temp_dir)
            replay_file = replay_dir / "raw_signals.jsonl"
            write_raw_signals(
                replay_file,
                [
                    RawSignal(
                        entity_name="Unrelated Corp",
                        client_id="demo-spacex-001",
                        signal_type=SignalType.NEWS,
                        source="unit_test",
                        content="Unrelated Corp faces fraud investigation over offshore governance concerns.",
                        timestamp=datetime.now(timezone.utc),
                        metadata={"title": "Unrelated Corp faces fraud investigation"},
                    )
                ],
            )

            payload = run_layer1_pipeline(
                client_id="demo-spacex-001",
                limit=10,
                live=False,
                replay_file=str(replay_file),
            )

            self.assertEqual(len(payload["drift_events"]), 0)
            self.assertEqual(len(payload["dropped_signals"]), 1)
            self.assertEqual(
                payload["dropped_signals"][0]["drop_reason"],
                "irrelevant_to_monitored_client",
            )

    def test_drift_event_citation_carries_full_evidence_fields(self) -> None:
        baseline = load_layer1_baselines()["demo-spacex-001"]
        risky_signal = list(mock_company_news(baseline.client_id, baseline.legal_name))[1]
        signal = RawSignal(
            entity_name=risky_signal.entity_name,
            client_id=risky_signal.client_id,
            signal_type=risky_signal.signal_type,
            source=risky_signal.source,
            content=risky_signal.content,
            timestamp=risky_signal.timestamp,
            metadata={**risky_signal.metadata, "query": f"{baseline.legal_name} investigation"},
        )

        event = KeywordDriftEngine().score_signal(baseline, signal)

        self.assertIsNotNone(event)
        assert event is not None
        citation = event.citations[0]
        for field in (
            "title",
            "url",
            "published_at",
            "source",
            "provider",
            "query",
            "matched_risk_terms",
            "reason",
        ):
            self.assertIn(field, citation)
        self.assertEqual(citation["title"], signal.metadata["title"])
        self.assertEqual(citation["url"], signal.metadata["url"])
        self.assertEqual(citation["published_at"], signal.metadata["published_at"])
        self.assertEqual(citation["source"], "mock_news")
        self.assertEqual(citation["provider"], "mock")
        self.assertEqual(citation["query"], f"{baseline.legal_name} investigation")
        self.assertIn("investigation", citation["matched_risk_terms"])
        self.assertEqual(citation["reason"], event.rationale)


if __name__ == "__main__":
    unittest.main()
