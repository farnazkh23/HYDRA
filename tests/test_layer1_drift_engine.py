from __future__ import annotations

import unittest

from backend.collectors.news import mock_company_news
from backend.kyc.store import load_layer1_baselines
from stream_engine.drift_engine import KeywordDriftEngine
from stream_engine.scoring_config import (
    Layer1ScoringConfig,
    Layer1Thresholds,
    Layer1Weights,
    load_layer1_scoring_config,
)


class KeywordDriftEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = load_layer1_baselines()["demo-spacex-001"]
        self.engine = KeywordDriftEngine()

    def test_stable_signal_is_dropped(self) -> None:
        stable_signal = list(mock_company_news(self.baseline.client_id, self.baseline.legal_name))[0]

        event = self.engine.score_signal(self.baseline, stable_signal)

        self.assertIsNone(event)

    def test_scoring_config_loads_thresholds_and_weights(self) -> None:
        scoring_config = load_layer1_scoring_config()

        self.assertEqual(scoring_config.thresholds.emit_event, 0.35)
        self.assertEqual(scoring_config.thresholds.high, 0.65)
        self.assertEqual(scoring_config.thresholds.critical, 0.85)
        self.assertEqual(scoring_config.weights.risk_term, 0.18)
        self.assertEqual(scoring_config.weights.adverse_sentiment_cap, 0.12)

    def test_custom_threshold_can_suppress_risky_signal(self) -> None:
        strict_config = Layer1ScoringConfig(
            thresholds=Layer1Thresholds(emit_event=1.01, high=1.01, critical=1.01),
            weights=Layer1Weights(
                risk_term=0.18,
                risk_term_cap=0.75,
                baseline_mismatch=0.04,
                baseline_mismatch_cap=0.2,
                entity_match=0.1,
                adverse_sentiment_multiplier=0.12,
                adverse_sentiment_cap=0.12,
            ),
        )
        strict_engine = KeywordDriftEngine(scoring_config=strict_config)
        risky_signal = list(mock_company_news(self.baseline.client_id, self.baseline.legal_name))[1]

        event = strict_engine.score_signal(self.baseline, risky_signal)

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
        self.assertEqual(event.drift_score, 1.0)
        self.assertIn("investigation", event.matched_risk_terms)
        self.assertEqual(event.scoring_breakdown["risk_term_score"], 0.72)
        self.assertEqual(event.scoring_breakdown["adverse_sentiment_score"], 0.084)
        self.assertEqual(event.source_metadata["provider"], "mock")
        self.assertEqual(event.source_metadata["sentiment_score"], -0.7)
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
