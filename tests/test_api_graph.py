from __future__ import annotations

import unittest
from unittest.mock import patch

from backend import api


class GraphFromDbKgUpdatesTests(unittest.TestCase):
    def test_skips_null_and_non_dict_kg_update(self) -> None:
        alerts = [
            {"id": "a1", "reasoningTrace": {"kg_update": None}},
            {"id": "a2", "reasoningTrace": {"kg_update": "not-a-dict"}},
            {"id": "a3", "reasoningTrace": None},
            {"id": "a4"},
        ]
        with patch.object(api.db, "get_all_alerts", return_value=alerts):
            self.assertIsNone(api._graph_from_db_kg_updates())

    def test_builds_graph_from_applied_kg_update(self) -> None:
        alerts = [
            {
                "id": "a1",
                "reasoningTrace": {
                    "kg_update": {
                        "status": "applied",
                        "triples_added": [
                            {
                                "node_from": "SpaceX",
                                "relationship": "HAS_RISK_INDICATOR",
                                "node_to": "Sanctions Body",
                            }
                        ],
                    }
                },
            }
        ]
        with patch.object(api.db, "get_all_alerts", return_value=alerts):
            graph = api._graph_from_db_kg_updates()

        self.assertIsNotNone(graph)
        node_ids = {n["id"] for n in graph["nodes"]}
        self.assertIn("spacex", node_ids)
        self.assertEqual(len(graph["edges"]), 1)


class GetGraphEndpointTests(unittest.TestCase):
    def test_get_graph_falls_back_when_neo4j_and_db_graph_unavailable(self) -> None:
        with patch.object(api.db, "get_all_alerts", return_value=[
            {"id": "a1", "reasoningTrace": {"kg_update": None}},
        ]):
            with patch("backend.neo4j_client.get_live_graph", side_effect=Exception("no connection")):
                graph = api.get_graph()

        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)
        self.assertTrue(len(graph["nodes"]) > 0)


if __name__ == "__main__":
    unittest.main()
