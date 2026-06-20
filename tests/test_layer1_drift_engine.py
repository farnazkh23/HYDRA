from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from io import StringIO

from backend.collectors.news import mock_company_news
from backend.kyc.store import load_layer1_baselines
from backend.models import RawSignal, SignalType
from stream_engine.drift_engine import KeywordDriftEngine
from stream_engine.scoring_config import (
    Layer1ScoringConfig,
    Layer1Thresholds,
    Layer1Weights,
    load_layer1_scoring_config,
)
from stream_engine.vectorizer import build_default_dense_vectorizer


class KeywordDriftEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = load_layer1_baselines()["demo-spacex-001"]
        self.engine = KeywordDriftEngine()

    def test_stable_signal_is_dropped(self) -> None:
        stable_signal = list(mock_company_news(self.baseline.client_id, self.baseline.legal_name))[0]

        event = self.engine.score_signal(self.baseline, stable_signal)

        self.assertIsNone(event)

    def test_irrelevant_risky_signal_is_dropped_before_scoring(self) -> None:
        unrelated_signal = RawSignal(
            entity_name="Unrelated Corp",
            client_id=self.baseline.client_id,
            signal_type=SignalType.NEWS,
            source="unit_test",
            content="Unrelated Corp faces fraud investigation over offshore governance concerns.",
            timestamp=datetime.now(timezone.utc),
            metadata={"title": "Unrelated Corp faces fraud investigation"},
        )

        event = self.engine.score_signal(self.baseline, unrelated_signal)

        self.assertIsNone(event)

    def test_scoring_config_loads_thresholds_and_weights(self) -> None:
        scoring_config = load_layer1_scoring_config()

        self.assertEqual(scoring_config.thresholds.emit_event, 0.35)
        self.assertEqual(scoring_config.thresholds.high, 0.65)
        self.assertEqual(scoring_config.thresholds.critical, 0.85)
        self.assertEqual(scoring_config.weights.risk_term, 0.18)
        self.assertEqual(scoring_config.weights.adverse_sentiment_cap, 0.12)

    def test_spacex_baseline_has_nominal_behavior_context(self) -> None:
        baselines = load_layer1_baselines()

        self.assertEqual(len(baselines), 8)
        self.assertIn("demo-amazon-001", baselines)
        self.assertIn("demo-nvidia-001", baselines)
        self.assertIn("demo-binance-001", baselines)
        self.assertIn("demo-openai-001", baselines)
        self.assertIn("demo-apple-001", baselines)
        self.assertIn("demo-meta-001", baselines)
        self.assertIn("demo-tesla-001", baselines)
        self.assertIn("Starlink", self.baseline.monitored_public_entities)
        self.assertIn("Elon Musk", self.baseline.monitored_public_entities)
        self.assertIn("commercial satellite launches", self.baseline.expected_activity)
        self.assertEqual(self.baseline.domain, "spacex.com")
        self.assertIn("export-control", self.baseline.risk_appetite)
        self.assertIn("investigation", self.baseline.high_risk_keywords)
        self.assertIn("faa investigation", self.baseline.high_risk_keywords)

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

    def test_missing_onnx_model_path_falls_back_to_local_dense_encoder(self) -> None:
        stderr = StringIO()
        with patch.dict("os.environ", {"LAYER1_ONNX_MODEL_PATH": "/tmp/missing-layer1-model.onnx"}), patch(
            "sys.stderr",
            stderr,
        ):
            dense_vectorizer = build_default_dense_vectorizer()

        self.assertIn(
            dense_vectorizer.encoder,
            {"local_tfidf_embedding", "local_hashing_embedding"},
        )
        self.assertIn("ONNX dense encoder unavailable", stderr.getvalue())
        self.assertIn("falling back", stderr.getvalue())

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
        self.assertEqual(event.loop_a_trace["trace_mode"], "vae_compatible_proxy")
        self.assertIn(
            event.loop_a_trace["reconstruction_engine"],
            {
                "lightweight_vae_reconstruction",
                "local_pca_reconstruction",
                "vae_compatible_statistical_proxy",
            },
        )
        self.assertEqual(event.loop_a_trace["vae_reconstruction_error"], 1.0)
        self.assertEqual(event.loop_a_trace["drift_threshold"], 0.35)
        self.assertIn("nominal_mean", event.loop_a_trace["nominal_profile"])
        self.assertIn("fit_mode", event.loop_a_trace["nominal_profile"])
        if event.loop_a_trace["reconstruction_engine"] == "lightweight_vae_reconstruction":
            self.assertEqual(
                event.loop_a_trace["nominal_profile"]["fit_mode"],
                "lightweight_vae_baseline_80_20",
            )
            self.assertEqual(event.loop_a_trace["nominal_profile"]["latent_dimensions"], 2)
            self.assertEqual(event.loop_a_trace["nominal_profile"]["train_samples"], 8)
            self.assertEqual(event.loop_a_trace["nominal_profile"]["validation_samples"], 2)
            self.assertIn("vae_loss", event.loop_a_trace["nominal_profile"])
            self.assertIn("fallback_engine", event.loop_a_trace["nominal_profile"])
        self.assertIn("dynamic_threshold", event.scoring_breakdown)
        self.assertIn("reconstruction_error", event.scoring_breakdown)
        self.assertGreater(event.scoring_breakdown["source_recency_score"], 0.0)
        self.assertGreater(event.scoring_breakdown["source_reliability_score"], 0.0)
        self.assertGreater(event.scoring_breakdown["signal_type_score"], 0.0)
        self.assertEqual(event.scoring_breakdown["relevance_score"], 1.0)
        self.assertTrue(event.loop_a_trace["drift_detected"])
        self.assertEqual(event.loop_a_trace["relevance_gate"]["reason"], "matched_monitored_entity")
        self.assertIn("SpaceX", event.loop_a_trace["relevance_gate"]["matched_terms"])
        self.assertEqual(event.loop_a_trace["decision"], "DRIFT_EVENT emitted")
        self.assertEqual(event.loop_a_trace["tokens_used"], 0)
        self.assertIn("investigation", event.loop_a_trace["top_keywords_matched"])
        self.assertEqual(
            event.loop_a_trace["sparse_encoder"]["encoder"],
            "local_splade_style_sparse",
        )
        self.assertEqual(
            event.loop_a_trace["sparse_encoder"]["weighting"],
            "log_tf_keyword_entity",
        )
        self.assertIn(
            "risk::investigation",
            event.loop_a_trace["sparse_encoder"]["activations"],
        )
        self.assertIn(
            "entity::SpaceX",
            event.loop_a_trace["sparse_encoder"]["activations"],
        )
        self.assertIn(
            "Elon Musk",
            event.loop_a_trace["sparse_encoder"]["matched_entities"],
        )
        self.assertIn(
            event.loop_a_trace["dense_encoder"]["encoder"],
            {"local_onnx_transformer", "local_tfidf_embedding", "local_hashing_embedding"},
        )
        self.assertGreater(event.loop_a_trace["dense_encoder"]["dimensions"], 0)
        self.assertGreaterEqual(event.loop_a_trace["embedding_shift_score"], 0.0)
        self.assertLessEqual(event.loop_a_trace["embedding_shift_score"], 1.0)
        self.assertGreaterEqual(
            event.scoring_breakdown["dense_semantic_shift_score"],
            0.0,
        )
        self.assertLessEqual(
            event.scoring_breakdown["dense_semantic_shift_score"],
            1.0,
        )
        self.assertEqual(
            event.loop_a_trace["hybrid_encoder"]["encoder"],
            "local_sparse_dense_hybrid",
        )
        self.assertGreater(event.loop_a_trace["hybrid_encoder"]["hybrid_dimensions"], 32)
        self.assertIn(
            "semantic_hash",
            event.loop_a_trace["hybrid_encoder"]["feature_families"],
        )
        self.assertGreaterEqual(event.scoring_breakdown["hybrid_shift_score"], 0.0)
        self.assertLessEqual(event.scoring_breakdown["hybrid_shift_score"], 1.0)
        self.assertEqual(event.source_metadata["provider"], "mock")
        self.assertEqual(event.source_metadata["sentiment_score"], -0.7)
        self.assertEqual(event.source_metadata["signal_type_score"], 0.7)
        self.assertGreater(event.source_metadata["source_recency_score"], 0.0)
        self.assertGreater(event.source_metadata["source_reliability_score"], 0.0)
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

    def test_lawsuit_signal_uses_litigation_relationship_hint(self) -> None:
        lawsuit_signal = list(mock_company_news(self.baseline.client_id, self.baseline.legal_name))[2]

        event = self.engine.score_signal(self.baseline, lawsuit_signal)

        self.assertIsNotNone(event)
        assert event is not None
        self.assertIn("litigation", event.source_metadata["relationship_hints"])
        self.assertNotIn("regulatory_investigation", event.source_metadata["relationship_hints"])


if __name__ == "__main__":
    unittest.main()
