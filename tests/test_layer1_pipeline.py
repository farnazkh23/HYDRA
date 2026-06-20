from __future__ import annotations

import tempfile
import unittest
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.models import RawSignal, SignalType
from backend.replay import load_raw_signals, write_raw_signals
from main import _write_replay_outputs, run_layer1_pipeline


class Layer1PipelineTests(unittest.TestCase):
    def test_mock_pipeline_emits_events_and_metrics(self) -> None:
        payload = run_layer1_pipeline(
            client_id="demo-spacex-001",
            limit=10,
            live=False,
        )

        self.assertEqual(len(payload["raw_signals"]), 3)
        self.assertEqual(len(payload["drift_events"]), 2)
        self.assertEqual(len(payload["dropped_signals"]), 1)
        self.assertEqual(payload["layer1_metrics"]["mode"], "mock")
        self.assertEqual(payload["layer1_metrics"]["signals_processed"], 3)
        self.assertEqual(payload["layer1_metrics"]["events_emitted"], 2)
        self.assertEqual(payload["layer1_metrics"]["signals_dropped"], 1)
        self.assertEqual(payload["layer1_metrics"]["drop_rate"], 0.3333)
        self.assertEqual(payload["layer1_metrics"]["news_queries"], 0)
        self.assertTrue(
            all(
                event["layer1_cost_units"]["news_queries"] == 0.0
                for event in payload["drift_events"]
            )
        )

    def test_mock_pipeline_supports_frontend_portfolio_personas(self) -> None:
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
            self.assertEqual(len(payload["raw_signals"]), 3)
            self.assertGreaterEqual(len(payload["drift_events"]), 1)

    def test_frontend_portfolio_personas_use_expected_key_people(self) -> None:
        expected_people = {
            "demo-amazon-001": "Jeff Bezos",
            "demo-nvidia-001": "Jensen Huang",
            "demo-binance-001": "Richard Teng",
            "demo-openai-001": "Sam Altman",
            "demo-apple-001": "Tim Cook",
            "demo-meta-001": "Mark Zuckerberg",
        }
        for client_id, expected_person in expected_people.items():
            payload = run_layer1_pipeline(
                client_id=client_id,
                limit=10,
                live=False,
            )

            event_entities = [
                entity
                for event in payload["drift_events"]
                for entity in event["source_metadata"]["related_entities"]
            ]
            self.assertIn(expected_person, event_entities)

    def test_audit_log_records_accepted_and_dropped_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_dir = Path(temp_dir) / "audit"
            payload = run_layer1_pipeline(
                client_id="demo-spacex-001",
                limit=10,
                live=False,
                audit_log_dir=audit_dir,
            )
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
            original = run_layer1_pipeline(
                client_id="demo-spacex-001",
                limit=10,
                live=False,
            )
            _write_replay_outputs(replay_dir, original)

            self.assertEqual(len(load_raw_signals(replay_dir / "raw_signals.jsonl")), 3)
            self.assertEqual((replay_dir / "drift_events.jsonl").read_text().count("\n"), 2)
            self.assertEqual((replay_dir / "dropped_signals.jsonl").read_text().count("\n"), 1)
            self.assertEqual((replay_dir / "layer1_metrics.jsonl").read_text().count("\n"), 1)

            replayed = run_layer1_pipeline(
                client_id="demo-spacex-001",
                limit=10,
                live=False,
                replay_file=str(replay_dir / "raw_signals.jsonl"),
            )

            self.assertEqual(len(replayed["drift_events"]), 2)
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
            snapshot_dir = Path(temp_dir) / "vae_snapshots"
            first_run = run_layer1_pipeline(
                client_id="demo-spacex-001",
                limit=10,
                live=False,
                vae_snapshot_dir=snapshot_dir,
            )

            self.assertEqual(len(first_run["dropped_signals"]), 1)
            self.assertTrue(first_run["dropped_signals"][0]["vae_snapshot_saved"])
            self.assertEqual((snapshot_dir / "demo-spacex-001.jsonl").read_text().count("\n"), 1)

            second_run = run_layer1_pipeline(
                client_id="demo-spacex-001",
                limit=10,
                live=False,
                vae_snapshot_dir=snapshot_dir,
            )
            snapshot_counts = [
                event["loop_a_trace"]["nominal_profile"]["time_series_snapshots"]
                for event in second_run["drift_events"]
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


if __name__ == "__main__":
    unittest.main()
