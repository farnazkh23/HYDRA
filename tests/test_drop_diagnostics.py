from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.kyc.store import load_layer1_baselines
from backend.models import RawSignal, SignalType
from backend.replay import write_raw_signals
from main import run_layer1_pipeline
from stream_engine.drift_engine import (
    KeywordDriftEngine,
    _matches_monitored_entity,
    _monitored_entities_in_text,
)


def _elon_musk_baseline():
    return load_layer1_baselines()["person_elon_musk"]


class MatchesMonitoredEntityTests(unittest.TestCase):
    def test_matches_via_legal_name(self) -> None:
        baseline = _elon_musk_baseline()
        self.assertTrue(_matches_monitored_entity(baseline, "coverage of elon musk today"))

    def test_matches_via_other_monitored_entity_not_just_legal_name(self) -> None:
        baseline = _elon_musk_baseline()
        # "Tesla" is in monitored_public_entities but is not baseline.legal_name.
        self.assertTrue(_matches_monitored_entity(baseline, "tesla announces new factory"))

    def test_does_not_match_unrelated_text(self) -> None:
        baseline = _elon_musk_baseline()
        self.assertFalse(_matches_monitored_entity(baseline, "unrelated corp quarterly earnings"))


class MonitoredEntitiesInTextDedupeTests(unittest.TestCase):
    def test_legal_name_duplicated_in_monitored_public_entities_is_not_repeated(self) -> None:
        # person_elon_musk's legal_name ("Elon Musk") is also itself listed in
        # monitored_public_entities - a real citation must not show
        # "Elon Musk, Elon Musk, Tesla" as evidence.
        baseline = _elon_musk_baseline()
        matched = _monitored_entities_in_text(baseline, "elon musk and tesla both mentioned here")
        self.assertEqual(matched, sorted(set(matched), key=matched.index))
        self.assertEqual(len(matched), len(set(m.lower() for m in matched)))


class ExplainDropTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = _elon_musk_baseline()
        self.engine = KeywordDriftEngine()

    def _signal(self, content: str, title: str, **metadata) -> RawSignal:
        return RawSignal(
            entity_name="Elon Musk",
            client_id="person_elon_musk",
            signal_type=SignalType.NEWS,
            source="unit_test",
            content=content,
            timestamp=datetime.now(timezone.utc),
            metadata={"title": title, **metadata},
        )

    def test_irrelevant_signal_reports_irrelevant_category(self) -> None:
        signal = self._signal("Unrelated Corp posts quarterly earnings.", "Unrelated Corp earnings")
        diagnostics = self.engine.explain_drop(self.baseline, signal)
        self.assertEqual(diagnostics["drop_category"], "irrelevant_to_monitored_client")
        self.assertEqual(diagnostics["matched_risk_terms"], [])
        self.assertIsNone(diagnostics["heuristic_score"])

    def test_relevant_signal_with_no_risk_terms_reports_that_category(self) -> None:
        signal = self._signal(
            "Elon Musk unveils new Tesla product roadmap at investor day.",
            "Tesla product roadmap",
        )
        diagnostics = self.engine.explain_drop(self.baseline, signal)
        self.assertEqual(diagnostics["drop_category"], "no_risk_terms_matched")
        self.assertEqual(diagnostics["matched_risk_terms"], [])
        self.assertIsNotNone(diagnostics["heuristic_score"])

    def test_relevant_signal_with_risk_terms_below_threshold_reports_that_category(self) -> None:
        # An artificially high threshold (independent of production tuning in
        # config/layer1_scoring.json) deterministically forces the "matched a
        # real risk term but still didn't clear the bar" branch, regardless
        # of how the production weights/threshold are calibrated.
        from stream_engine.scoring_config import Layer1ScoringConfig, Layer1Thresholds, Layer1Weights

        strict_config = Layer1ScoringConfig(
            thresholds=Layer1Thresholds(emit_event=0.99, high=0.995, critical=0.999),
            weights=self.engine.scoring_config.weights,
        )
        strict_engine = KeywordDriftEngine(scoring_config=strict_config)
        signal = self._signal(
            "Tesla faces a minor governance question raised by a shareholder.",
            "Tesla shareholder governance question",
        )

        diagnostics = strict_engine.explain_drop(self.baseline, signal)
        event = strict_engine.score_signal(self.baseline, signal)

        self.assertIsNone(event)
        self.assertEqual(diagnostics["drop_category"], "below_drift_threshold")
        self.assertTrue(diagnostics["matched_risk_terms"])
        self.assertLess(diagnostics["heuristic_score"], diagnostics["drift_threshold"])


class EntityScoreBroadenedForRelevantSignalsTests(unittest.TestCase):
    """
    Confirms score_signal's entity-match bonus now credits any monitored
    public entity (e.g. "Tesla"), not only the exact legal_name ("Elon
    Musk") - a real Tesla-focused risk article should be able to emit an
    evidence-backed alert even if it never says "Elon Musk" verbatim.
    """

    def test_tesla_only_mention_with_risk_terms_can_emit(self) -> None:
        baseline = _elon_musk_baseline()
        engine = KeywordDriftEngine()
        signal = RawSignal(
            entity_name="Tesla",
            client_id="person_elon_musk",
            signal_type=SignalType.NEWS,
            source="unit_test",
            content=(
                "Tesla is facing a governance investigation after a lawsuit "
                "alleged offshore financing irregularities tied to the company."
            ),
            timestamp=datetime.now(timezone.utc),
            metadata={"title": "Tesla governance investigation", "provider": "unit_test_wire"},
        )

        diagnostics = engine.explain_drop(baseline, signal)
        event = engine.score_signal(baseline, signal)

        # With >=1 real global risk term matched and the broadened entity
        # bonus, this should not be silently dropped as pure noise.
        self.assertTrue(diagnostics["matched_risk_terms"])
        if event is None:
            self.fail(
                f"Expected an evidence-backed DriftEvent for a Tesla-mention "
                f"risk article; got diagnostics={diagnostics}"
            )
        self.assertGreater(len(event.citations), 0)


class WeakEntityLinkTitleMismatchTests(unittest.TestCase):
    """
    An article that mentions the monitored entity only in the body, never in
    the title, is weak evidence - a reader glancing at the citation title
    would not see why it's linked to the monitored profile. Such signals
    must be dropped with a clear category, not turned into an alert.
    """

    def setUp(self) -> None:
        self.baseline = _elon_musk_baseline()
        self.engine = KeywordDriftEngine()

    def _content_only_signal(self) -> RawSignal:
        return RawSignal(
            entity_name="Tesla",
            client_id="person_elon_musk",
            signal_type=SignalType.NEWS,
            source="unit_test",
            content=(
                "Industry roundup: several automakers faced scrutiny this week. "
                "Tesla was named in passing amid a broader governance investigation "
                "and lawsuit affecting the sector."
            ),
            timestamp=datetime.now(timezone.utc),
            metadata={
                "title": "Automaker industry roundup: governance investigations widen",
                "provider": "unit_test_wire",
                "query": "Elon Musk investigation",
                "url": "https://example.com/roundup",
            },
        )

    def test_content_only_mention_is_dropped_not_alerted(self) -> None:
        signal = self._content_only_signal()
        event = self.engine.score_signal(self.baseline, signal)
        self.assertIsNone(event)

    def test_content_only_mention_reports_weak_entity_link_category(self) -> None:
        signal = self._content_only_signal()
        diagnostics = self.engine.explain_drop(self.baseline, signal)
        self.assertEqual(diagnostics["drop_category"], "weak_entity_link_title_mismatch")
        # Confirmed present in the body, for transparency, even though it
        # didn't clear the (stricter) title bar.
        self.assertIn("Tesla", diagnostics["matched_entities"])
        self.assertIsNone(diagnostics["heuristic_score"])

    def test_title_confirmed_entity_still_emits_with_citation_evidence(self) -> None:
        signal = RawSignal(
            entity_name="Tesla",
            client_id="person_elon_musk",
            signal_type=SignalType.NEWS,
            source="unit_test",
            content=(
                "Tesla faces a governance investigation after a lawsuit alleged "
                "offshore financing irregularities tied to the company."
            ),
            timestamp=datetime.now(timezone.utc),
            metadata={
                "title": "Tesla governance investigation widens",
                "provider": "unit_test_wire",
                "query": "Tesla investigation",
                "url": "https://example.com/tesla-investigation",
            },
        )

        event = self.engine.score_signal(self.baseline, signal)

        self.assertIsNotNone(event)
        citation = event.citations[0]
        self.assertIn("Tesla", citation["matched_entities"])
        self.assertIn("Tesla", citation["entity_link_reason"])
        self.assertEqual(citation["provider"], "unit_test_wire")
        self.assertEqual(citation["url"], "https://example.com/tesla-investigation")


class DroppedSignalDiagnosticsSurfaceInPipelineTests(unittest.TestCase):
    def test_dropped_signals_include_metadata_and_categories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_file = Path(temp_dir) / "raw_signals.jsonl"
            write_raw_signals(
                replay_file,
                [
                    RawSignal(
                        entity_name="Unrelated Corp",
                        client_id="person_elon_musk",
                        signal_type=SignalType.NEWS,
                        source="unit_test",
                        content="Unrelated Corp posts quarterly earnings.",
                        timestamp=datetime.now(timezone.utc),
                        metadata={
                            "title": "Unrelated Corp earnings",
                            "provider": "unit_test_wire",
                            "query": "Unrelated Corp",
                            "url": "https://example.com/unrelated",
                        },
                    )
                ],
            )

            payload = run_layer1_pipeline(
                client_id="person_elon_musk",
                limit=10,
                live=False,
                replay_file=str(replay_file),
            )

        self.assertEqual(len(payload["dropped_signals"]), 1)
        dropped = payload["dropped_signals"][0]
        self.assertEqual(dropped["drop_category"], "irrelevant_to_monitored_client")
        self.assertEqual(dropped["provider"], "unit_test_wire")
        self.assertEqual(dropped["query"], "Unrelated Corp")
        self.assertEqual(dropped["url"], "https://example.com/unrelated")
        self.assertIn("matched_risk_terms", dropped)
        self.assertIn("heuristic_score", dropped)


if __name__ == "__main__":
    unittest.main()
