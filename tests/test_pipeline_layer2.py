from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

import pandas as pd

import main
from analytic_engine.router import ComplianceAuditLog
from backend import api


def _sample_drift_event(client_id: str = "person_elon_musk") -> dict:
    return {
        "event_id": "evt-test-1",
        "client_id": client_id,
        "client_name": "Elon Musk",
        "severity": "high",
        "matched_risk_terms": ["investigation"],
        "rationale": "Test rationale for unit test drift event.",
        "triggered_at": "2026-08-03T00:00:00+00:00",
        "citations": [{"url": "https://example.com/article-1"}],
        "drift_score": 0.9,
        "source_metadata": {},
        "layer1_cost_units": {"news_queries": 0.0, "llm_tokens": 0.0, "heavy_reasoner_calls": 0.0},
        "scoring_breakdown": {"relevance_score": 1.0},
        "loop_a_trace": {},
    }


def _sample_history_df() -> pd.DataFrame:
    dates = pd.date_range(start="2026-05-01", end="2026-05-10", freq="D")
    return pd.DataFrame({"timestamp": dates, "value": [150] * len(dates)})


class FakeTsEngine:
    def detect_volumetric_anomaly(self, df):
        return False, {
            "forecasted_mean": 150.0,
            "anomaly_flag": False,
            "severity_score": 0.0,
            "engine_status": "production_live_nixtla",
        }


class FakeGraphEngine:
    def __init__(self) -> None:
        self.driver = object()  # simulates a live Neo4j connection

    def execute_triple_resolution(self, payload, timestamp):
        return {"total_active_edges": 3.0, "triples_added_count": 1.0, "triples_deleted_count": 0.0}

    def close(self) -> None:
        pass


class FakeSurvivalModel:
    def __init__(self) -> None:
        self.is_mocked = False

    def calculate_time_to_decay(self, matrix_x):
        return 5.0, 0.5


class FakeRouter:
    def __init__(self) -> None:
        self.client = object()  # simulates a live Apertus client
        self.token_ledger = {"cheap_tier_calls": 0, "heavy_tier_calls": 1, "total_cost_usd": 0.00015}

    def evaluate_routing_tier(self, client_id, predicted_t, raw_context_signal):
        return ComplianceAuditLog(
            risk_token="CRITICAL_BREACH",
            chain_of_thought="Test chain of thought.",
            audit_citations=["https://example.com/article-1"],
        )


class ExecuteHydraPipelineModelStatusTests(unittest.TestCase):
    def test_returns_model_status_reflecting_live_components(self) -> None:
        with patch.object(main, "InternalTelemetryEngine", FakeTsEngine), \
             patch.object(main, "TemporalGraphFusionEngine", FakeGraphEngine), \
             patch.object(main, "BaseSurvivalModel", FakeSurvivalModel), \
             patch.object(main, "CostAwareCascadingRouter", FakeRouter):
            result = asyncio.run(main.execute_hydra_pipeline(_sample_drift_event(), _sample_history_df()))

        self.assertIn("audit_log", result)
        self.assertIn("model_status", result)
        self.assertEqual(result["audit_log"].risk_token, "CRITICAL_BREACH")
        self.assertEqual(result["model_status"]["timegpt"]["engine_status"], "production_live_nixtla")
        self.assertEqual(result["model_status"]["survival_model"]["mode"], "trained_weights")
        self.assertEqual(result["model_status"]["graph_fusion"]["mode"], "live_neo4j")
        self.assertEqual(result["model_status"]["router"]["mode"], "live_apertus")

    def test_reports_fallback_mode_when_components_are_unconfigured(self) -> None:
        # No patching: exercises the real analytic_engine classes, which all
        # self-report "fallback" modes when their respective API keys/live
        # connections are unavailable (the case in this test environment).
        result = asyncio.run(main.execute_hydra_pipeline(_sample_drift_event(), _sample_history_df()))

        self.assertEqual(result["model_status"]["timegpt"]["engine_status"], "local_heuristic_fallback")
        self.assertEqual(result["model_status"]["survival_model"]["mode"], "heuristic_proxy")
        self.assertEqual(result["model_status"]["graph_fusion"]["mode"], "local_fallback")
        self.assertEqual(result["model_status"]["router"]["mode"], "local_fallback")


class TriggerPipelineLayer2WiringTests(unittest.TestCase):
    def _canned_layer1_result(self, client_id: str) -> dict:
        return {
            "drift_events": [_sample_drift_event(client_id)],
            "dropped_signals": [
                {
                    "title": "Unrelated Corp earnings",
                    "provider": "unit_test_wire",
                    "query": "Unrelated Corp",
                    "url": "https://example.com/unrelated",
                    "drop_reason": "irrelevant_to_monitored_client",
                    "drop_category": "irrelevant_to_monitored_client",
                }
            ],
            "layer1_metrics": {
                "signals_processed": 2,
                "signals_dropped": 1,
                "events_emitted": 1,
            },
        }

    def test_dropped_signals_are_returned_in_response(self) -> None:
        with patch.object(api, "run_layer1_pipeline", return_value=self._canned_layer1_result("person_elon_musk")), \
             patch.object(api.db, "upsert_alert"), \
             patch.object(api, "_run_layer2", return_value=None):
            response = api.trigger_pipeline({"client_id": "person_elon_musk", "live": True})

        self.assertEqual(len(response["dropped_signals"]), 1)
        dropped = response["dropped_signals"][0]
        self.assertEqual(dropped["provider"], "unit_test_wire")
        self.assertEqual(dropped["url"], "https://example.com/unrelated")
        self.assertEqual(dropped["drop_category"], "irrelevant_to_monitored_client")

    def test_live_non_replay_run_attaches_model_status_to_loop_b(self) -> None:
        canned_loop_b = {
            "router": {"path": "heavy"},
            "model_status": {
                "timegpt": {"engine_status": "production_live_nixtla"},
                "survival_model": {"mode": "trained_weights"},
                "graph_fusion": {"mode": "live_neo4j"},
                "router": {"mode": "live_apertus"},
            },
        }
        with patch.object(api, "run_layer1_pipeline", return_value=self._canned_layer1_result("person_elon_musk")), \
             patch.object(api.db, "upsert_alert"), \
             patch.object(api, "_run_layer2", return_value=canned_loop_b) as mock_run_layer2:
            response = api.trigger_pipeline({"client_id": "person_elon_musk", "live": True})

        mock_run_layer2.assert_called_once()
        alert = response["alerts"][0]
        self.assertEqual(alert["reasoningTrace"]["loop_b"], canned_loop_b)
        self.assertNotIn("loop_b_skip_reason", alert["reasoningTrace"])
        self.assertEqual(alert["dataSource"], "live")
        self.assertEqual(response["data_source"], "live")

    def test_replay_run_skips_layer2_with_honest_reason(self) -> None:
        with patch.object(api, "run_layer1_pipeline", return_value=self._canned_layer1_result("person_elon_musk")), \
             patch.object(api.db, "upsert_alert"), \
             patch.object(api, "_run_layer2") as mock_run_layer2:
            response = api.trigger_pipeline({
                "client_id": "person_elon_musk",
                "live": False,
                "replay_fixture": True,
            })

        mock_run_layer2.assert_not_called()
        alert = response["alerts"][0]
        self.assertIsNone(alert["reasoningTrace"]["loop_b"])
        self.assertIn("Replay fixture mode", alert["reasoningTrace"]["loop_b_skip_reason"])
        self.assertEqual(alert["dataSource"], "replay_fixture")
        self.assertEqual(response["data_source"], "replay_fixture")

    def test_non_live_run_skips_layer2_with_honest_reason(self) -> None:
        with patch.object(api, "run_layer1_pipeline", return_value=self._canned_layer1_result("person_elon_musk")), \
             patch.object(api.db, "upsert_alert"), \
             patch.object(api, "_run_layer2") as mock_run_layer2:
            response = api.trigger_pipeline({"client_id": "person_elon_musk", "live": False})

        mock_run_layer2.assert_not_called()
        alert = response["alerts"][0]
        self.assertIsNone(alert["reasoningTrace"]["loop_b"])
        self.assertIn("only run when live=true", alert["reasoningTrace"]["loop_b_skip_reason"])
        self.assertEqual(alert["dataSource"], "mock")
        self.assertEqual(response["data_source"], "mock")


if __name__ == "__main__":
    unittest.main()
