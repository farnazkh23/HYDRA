from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.replay import load_raw_signals
from main import _write_replay_outputs, run_layer1_pipeline


class Layer1PipelineTests(unittest.TestCase):
    def test_mock_pipeline_emits_events_and_metrics(self) -> None:
        payload = run_layer1_pipeline(
            client_id="demo-aminaclient-001",
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

    def test_replay_round_trip_does_not_require_live_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_dir = Path(temp_dir)
            original = run_layer1_pipeline(
                client_id="demo-aminaclient-001",
                limit=10,
                live=False,
            )
            _write_replay_outputs(replay_dir, original)

            self.assertEqual(len(load_raw_signals(replay_dir / "raw_signals.jsonl")), 3)
            self.assertEqual((replay_dir / "drift_events.jsonl").read_text().count("\n"), 2)
            self.assertEqual((replay_dir / "dropped_signals.jsonl").read_text().count("\n"), 1)
            self.assertEqual((replay_dir / "layer1_metrics.jsonl").read_text().count("\n"), 1)

            replayed = run_layer1_pipeline(
                client_id="demo-aminaclient-001",
                limit=10,
                live=False,
                replay_file=str(replay_dir / "raw_signals.jsonl"),
            )

            self.assertEqual(len(replayed["drift_events"]), 2)
            self.assertEqual(replayed["layer1_metrics"]["mode"], "replay")
            self.assertEqual(replayed["layer1_metrics"]["news_queries"], 0)


if __name__ == "__main__":
    unittest.main()
