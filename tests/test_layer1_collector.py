from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.collectors.news import EventRegistryNewsCollector, _expanded_news_queries, dedupe_signals
from backend.models import RawSignal, SignalType


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

    def test_adverse_query_expansion_keeps_base_query_first(self) -> None:
        queries = _expanded_news_queries("SpaceX", expand_adverse_queries=True)

        self.assertEqual(queries[0], "SpaceX")
        self.assertIn("SpaceX investigation", queries)
        self.assertIn("SpaceX export control", queries)

    def test_live_signal_deduplication_prefers_first_url(self) -> None:
        now = datetime.now(timezone.utc)
        first = RawSignal(
            entity_name="SpaceX",
            client_id="demo-spacex-001",
            signal_type=SignalType.NEWS,
            source="event_registry/source_a",
            content="SpaceX investigation",
            timestamp=now,
            metadata={"title": "SpaceX investigation", "url": "https://example.com/a"},
        )
        duplicate = RawSignal(
            entity_name="SpaceX",
            client_id="demo-spacex-001",
            signal_type=SignalType.NEWS,
            source="event_registry/source_b",
            content="SpaceX investigation duplicate",
            timestamp=now,
            metadata={"title": "Different title", "url": "https://example.com/a"},
        )

        signals = dedupe_signals([first, duplicate])

        self.assertEqual(signals, [first])

    def test_live_signal_deduplication_prefers_first_title(self) -> None:
        now = datetime.now(timezone.utc)
        first = RawSignal(
            entity_name="SpaceX",
            client_id="demo-spacex-001",
            signal_type=SignalType.NEWS,
            source="event_registry/source_a",
            content="SpaceX mishap investigation",
            timestamp=now,
            metadata={"title": "SpaceX mishap investigation", "url": "https://example.com/a"},
        )
        duplicate = RawSignal(
            entity_name="SpaceX",
            client_id="demo-spacex-001",
            signal_type=SignalType.NEWS,
            source="event_registry/source_b",
            content="SpaceX mishap investigation syndicated copy",
            timestamp=now,
            metadata={"title": "SpaceX mishap investigation", "url": "https://example.com/b"},
        )

        signals = dedupe_signals([first, duplicate])

        self.assertEqual(signals, [first])


if __name__ == "__main__":
    unittest.main()
