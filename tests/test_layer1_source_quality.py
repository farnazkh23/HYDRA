from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from backend.models import RawSignal, SignalType
from stream_engine.source_quality import score_source_quality


class SourceQualityTests(unittest.TestCase):
    def test_recent_reliable_news_scores_high(self) -> None:
        now = datetime(2026, 6, 20, tzinfo=timezone.utc)
        signal = RawSignal(
            entity_name="SpaceX",
            client_id="demo-spacex-001",
            signal_type=SignalType.NEWS,
            source="event_registry/Reuters",
            content="SpaceX faces investigation",
            timestamp=now,
            metadata={
                "provider": "event_registry",
                "published_at": now.isoformat(),
                "url": "https://reuters.com/example",
            },
        )

        scores = score_source_quality(signal, now=now)

        self.assertEqual(scores.recency_score, 1.0)
        self.assertEqual(scores.reliability_score, 0.9)
        self.assertEqual(scores.signal_type_score, 0.7)

    def test_old_unknown_source_scores_lower(self) -> None:
        now = datetime(2026, 6, 20, tzinfo=timezone.utc)
        signal = RawSignal(
            entity_name="SpaceX",
            client_id="demo-spacex-001",
            signal_type=SignalType.NEWS,
            source="unknown_blog",
            content="SpaceX commentary",
            timestamp=now - timedelta(days=120),
            metadata={},
        )

        scores = score_source_quality(signal, now=now)

        self.assertEqual(scores.recency_score, 0.1)
        self.assertEqual(scores.reliability_score, 0.5)
        self.assertEqual(scores.signal_type_score, 0.7)


if __name__ == "__main__":
    unittest.main()
