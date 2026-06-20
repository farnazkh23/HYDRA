from __future__ import annotations

import unittest

from backend.collectors.news import EventRegistryNewsCollector
from backend.models import SignalType


class EventRegistryNewsCollectorTests(unittest.TestCase):
    def test_disabled_collector_uses_mock_fallback(self) -> None:
        collector = EventRegistryNewsCollector(enabled=False)

        signals = collector.fetch_company_news(
            client_id="demo-spacex-001",
            company_name="SpaceX",
            limit=10,
        )

        self.assertEqual(len(signals), 3)
        self.assertTrue(all(signal.source == "mock_news" for signal in signals))
        self.assertTrue(all(signal.signal_type == SignalType.NEWS for signal in signals))
        self.assertTrue(all(signal.metadata.get("signal_id") for signal in signals))


if __name__ == "__main__":
    unittest.main()
