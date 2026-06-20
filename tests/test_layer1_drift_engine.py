from __future__ import annotations

import unittest

from backend.collectors.news import mock_company_news
from backend.kyc.store import load_layer1_baselines
from stream_engine.drift_engine import KeywordDriftEngine


class KeywordDriftEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = load_layer1_baselines()["demo-spacex-001"]
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
        self.assertEqual(event.severity.value, "critical")
        self.assertEqual(event.drift_score, 0.98)
        self.assertIn("investigation", event.matched_risk_terms)
        self.assertEqual(event.scoring_breakdown["risk_term_score"], 0.72)
        self.assertEqual(event.source_metadata["provider"], "mock")
        self.assertIn("Elon Musk", event.source_metadata["related_entities"])
        self.assertIn("Orbital Ventures Ltd", event.source_metadata["related_entities"])
        self.assertIn("offshore_link", event.source_metadata["relationship_hints"])
        self.assertEqual(
            event.source_metadata["entity_roles"]["Orbital Ventures Ltd"],
            "partner_or_counterparty",
        )

    def test_spacex_signal_extracts_elon_relationship_context(self) -> None:
        risky_signal = list(mock_company_news(self.baseline.client_id, self.baseline.legal_name))[1]

        event = self.engine.score_signal(self.baseline, risky_signal)

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.client_name, "SpaceX")
        self.assertIn("Elon Musk", event.source_metadata["related_entities"])
        self.assertIn("Orbital Ventures Ltd", event.source_metadata["related_entities"])
        self.assertIn("regulatory_investigation", event.source_metadata["relationship_hints"])
        self.assertIn("offshore_link", event.source_metadata["relationship_hints"])
        self.assertEqual(
            event.source_metadata["entity_roles"]["Elon Musk"],
            "beneficial_owner_or_key_person",
        )


if __name__ == "__main__":
    unittest.main()
