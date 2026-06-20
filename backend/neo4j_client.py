from __future__ import annotations

import os
from typing import Any

_driver = None


def _get_driver():
    global _driver
    if _driver is not None:
        return _driver
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", f"neo4j+s://{os.getenv('NEO4J_USERNAME', 'neo4j')}.databases.neo4j.io")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        _driver = GraphDatabase.driver(uri, auth=(username, password))
        _driver.verify_connectivity()
        print("[Neo4j] Connected to Aura instance.")
    except Exception as exc:
        print(f"[Neo4j] Connection failed: {exc}")
        _driver = None
    return _driver


def get_live_graph(company_names: list[str]) -> dict[str, Any] | None:
    """
    Query Neo4j for nodes and relationships relevant to the given companies.
    Returns a graph shape compatible with the frontend NetworkGraph component,
    or None if Neo4j is unavailable.
    """
    driver = _get_driver()
    if not driver:
        return None

    try:
        with driver.session() as session:
            # Fetch all entity nodes that are connected to our portfolio companies
            node_result = session.run(
                """
                MATCH (c:Company)
                WHERE c.name IN $names
                OPTIONAL MATCH (c)-[r]-(related)
                RETURN c, r, related
                LIMIT 200
                """,
                names=company_names,
            )

            nodes: dict[str, dict[str, Any]] = {}
            edges: list[dict[str, Any]] = []
            seen_edges: set[tuple[str, str, str]] = set()

            for record in node_result:
                c = record["c"]
                r = record["r"]
                related = record["related"]

                # Add the company node
                c_id = str(c.element_id)
                c_name = c.get("name", c_id)
                if c_id not in nodes:
                    nodes[c_id] = {
                        "id": c_id,
                        "label": c_name,
                        "type": "company",
                        "riskStatus": "medium",
                        "driftScore": 0,
                        "lastUpdated": "live",
                    }

                if r is None or related is None:
                    continue

                # Add the related entity node
                rel_id = str(related.element_id)
                rel_name = related.get("name", rel_id)
                rel_labels = list(related.labels)
                rel_type = rel_labels[0].lower() if rel_labels else "entity"
                if rel_id not in nodes:
                    nodes[rel_id] = {
                        "id": rel_id,
                        "label": rel_name,
                        "type": rel_type,
                        "riskStatus": "low",
                        "driftScore": 0,
                        "lastUpdated": "live",
                    }

                # Add edge (deduplicated)
                rel_type_name = r.type
                source_id = str(r.start_node.element_id)
                target_id = str(r.end_node.element_id)
                edge_key = (source_id, target_id, rel_type_name)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        "source": source_id,
                        "target": target_id,
                        "relationship": rel_type_name.replace("_", " ").lower(),
                    })

            if not nodes:
                return None

            return {"nodes": list(nodes.values()), "edges": edges}

    except Exception as exc:
        print(f"[Neo4j] Query failed: {exc}")
        return None


def get_active_triples(company_name: str) -> list[dict[str, Any]]:
    """Return active relationship triples for a company from Neo4j."""
    driver = _get_driver()
    if not driver:
        return []
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (s:Entity {name: $name})-[r {state: 'ACTIVE'}]->(o:Entity)
                RETURN s.name AS subject, type(r) AS predicate, o.name AS object, r.updated_at AS updated_at
                LIMIT 50
                """,
                name=company_name,
            )
            return [dict(record) for record in result]
    except Exception as exc:
        print(f"[Neo4j] Triple query failed: {exc}")
        return []
