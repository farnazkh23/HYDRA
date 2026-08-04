from __future__ import annotations

import unittest
from unittest.mock import patch

from backend import api
from backend.kyc.store import load_layer1_baselines
from main import _load_or_collect_signals


class GetAlertsDataSourceFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alerts = [
            {"id": "a-live", "dataSource": "live", "customerId": "person_elon_musk"},
            {"id": "a-replay", "dataSource": "replay_fixture", "customerId": "person_elon_musk"},
            {"id": "a-mock", "dataSource": "mock", "customerId": "person_elon_musk"},
            {"id": "a-legacy", "customerId": "person_elon_musk"},  # predates dataSource tagging
        ]

    def test_no_filter_returns_everything(self) -> None:
        with patch.object(api.db, "get_all_alerts", return_value=self.alerts):
            result = api.get_alerts()
        self.assertEqual(len(result), 4)

    def test_live_filter_excludes_replay_mock_and_untagged_legacy_alerts(self) -> None:
        with patch.object(api.db, "get_all_alerts", return_value=self.alerts):
            result = api.get_alerts(data_source="live")
        self.assertEqual([a["id"] for a in result], ["a-live"])

    def test_replay_filter_returns_only_replay_alerts(self) -> None:
        with patch.object(api.db, "get_all_alerts", return_value=self.alerts):
            result = api.get_alerts(data_source="replay_fixture")
        self.assertEqual([a["id"] for a in result], ["a-replay"])


class NewsCollectorStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = load_layer1_baselines()["person_elon_musk"]

    def test_replay_path_reports_replay_fixture_status(self) -> None:
        import tempfile
        from pathlib import Path

        from backend.replay import write_raw_signals
        from backend.collectors.news import mock_company_news

        with tempfile.TemporaryDirectory() as tmp:
            fixture_path = Path(tmp) / "raw_signals.jsonl"
            write_raw_signals(fixture_path, list(mock_company_news("person_elon_musk", "Elon Musk")))

            signals, queries, status = _load_or_collect_signals(
                baseline=self.baseline,
                limit=10,
                live=False,
                replay_file=str(fixture_path),
                expand_adverse_news=False,
            )

        self.assertEqual(status["path"], "replay_fixture")
        self.assertFalse(status["enabled"])
        self.assertFalse(status["api_key_configured"])
        self.assertEqual(status["queries_attempted"], 0)

    def test_non_live_path_reports_disabled_collector(self) -> None:
        signals, queries, status = _load_or_collect_signals(
            baseline=self.baseline,
            limit=10,
            live=False,
            replay_file=None,
            expand_adverse_news=False,
        )

        self.assertEqual(status["path"], "disabled_mock_mode")
        self.assertFalse(status["enabled"])
        self.assertEqual(status["queries_attempted"], 0)
        self.assertEqual(signals, [])

    def test_live_path_attempts_real_collector_and_reports_key_presence_only(self) -> None:
        # No EVENT_REGISTRY_API_KEY is configured in the test environment, so
        # this exercises the real collector's live (failing) HTTP attempts —
        # proving the live path is genuinely reached, not silently skipped.
        signals, queries, status = _load_or_collect_signals(
            baseline=self.baseline,
            limit=10,
            live=True,
            replay_file=None,
            expand_adverse_news=False,
        )

        self.assertEqual(status["path"], "event_registry_live_api")
        self.assertTrue(status["enabled"])
        self.assertFalse(status["api_key_configured"])
        self.assertGreater(status["queries_attempted"], 0)
        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()
