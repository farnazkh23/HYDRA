from __future__ import annotations

import unittest

from backend.collectors.news import mock_company_news
from backend.kyc.store import load_layer1_baselines
from stream_engine.drift_engine import KeywordDriftEngine


class KeywordDriftEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = load_layer1_baselines()["demo-aminaclient-001"]
        self.engine = KeywordDriftEngine()

    def test_stable_signal_is_dropped(self) -> None:
        stable_signal = list(mock_company_news(self.baseline.client_id, self.baseline.legal_name))[0]

        event = self.engine.score_signal(self.baseline, stable_signal)

        self.assertIsNone(event)

    def test_risky_signal_emits_versioned_drift_event(self) -> None:
        risky_signal = list(mock_company_news(self.baseline.client_id, self.baseline.legal_name))[1]

        event = self.engine.score_signal(self.baseline, risky_signal)

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.schema_version, "layer1.drift_event.v1")
        self.assertEqual(event.event_type, "DRIFT_EVENT")
        self.assertEqual(event.routing_hint, "layer2_structural_reasoning")
        self.assertEqual(event.severity.value, "high")
        self.assertEqual(event.drift_score, 0.84)
        self.assertIn("crypto exchange", event.matched_risk_terms)
        self.assertEqual(event.scoring_breakdown["risk_term_score"], 0.54)
        self.assertEqual(event.source_metadata["provider"], "mock")
        self.assertIn("Atlas Digital Ltd", event.source_metadata["related_entities"])
        self.assertIn("offshore_link", event.source_metadata["relationship_hints"])
        self.assertIn("business_pivot", event.source_metadata["relationship_hints"])
        self.assertEqual(
            event.source_metadata["entity_roles"]["Atlas Digital Ltd"],
            "ownership_related_entity",
        )


if __name__ == "__main__":
    unittest.main()
