from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

_driver = None

# Relationship vocabulary — matches KG-GNN-finance reference
VALID_RELATIONSHIPS = frozenset({
    "OWNS", "PARTNERS_WITH", "IS_ACTIVE_IN", "IS_MANAGED_BY",
    "WAS_FOUNDED_BY", "HAS_BOARD_MEMBER", "HAS_HEADQUARTER_IN",
    "OFFERS", "IS_LISTED_IN", "HAS_RISK_INDICATOR",
})

# Layer 1 entity_roles → KG relationship
_ROLE_TO_REL: dict[str, str] = {
    "ownership_related_entity":    "OWNS",
    "partner_or_counterparty":     "PARTNERS_WITH",
    "investigation_related_entity": "HAS_RISK_INDICATOR",
    "structural_risk_related_entity": "HAS_RISK_INDICATOR",
    "mentioned_related_entity":    "HAS_RISK_INDICATOR",
}

# Layer 1 relationship_hints → KG relationship (used as fallback / override)
_HINT_TO_REL: dict[str, str] = {
    "ownership":               "OWNS",
    "partnership":             "PARTNERS_WITH",
    "business_pivot":          "IS_ACTIVE_IN",
    "regulatory_investigation": "HAS_RISK_INDICATOR",
    "litigation":              "HAS_RISK_INDICATOR",
    "offshore_link":           "HAS_RISK_INDICATOR",
}


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def _get_driver():
    global _driver
    if _driver is not None:
        return _driver
    try:
        from neo4j import GraphDatabase
        uri = os.getenv(
            "NEO4J_URI",
            f"neo4j+s://{os.getenv('NEO4J_USERNAME', 'neo4j')}.databases.neo4j.io",
        )
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        _driver = GraphDatabase.driver(uri, auth=(username, password))
        _driver.verify_connectivity()
        print("[Neo4j] Connected to Aura instance.")
    except Exception as exc:
        print(f"[Neo4j] Connection failed: {exc}")
        _driver = None
    return _driver


# ---------------------------------------------------------------------------
# Triple helpers
# ---------------------------------------------------------------------------

def _triple_key(t: dict[str, str]) -> tuple[str, str, str]:
    return (t["node_from"], t["relationship"], t["node_to"])


def _extract_triples_from_drift_event(drift_event: dict[str, Any]) -> list[dict[str, str]]:
    """
    Rule-based extraction of KG triples from a HYDRA DRIFT_EVENT.

    Layer 1 already identifies entities and relationship hints from news signals.
    This maps that structured output to the KG-GNN-finance triple vocabulary
    without an extra LLM call.
    """
    client_name = drift_event.get("client_name", "")
    if not client_name:
        return []

    source_meta = drift_event.get("source_metadata", {})
    entity_roles: dict[str, str] = source_meta.get("entity_roles", {})
    hints: list[str] = source_meta.get("relationship_hints", [])
    matched_terms: list[str] = drift_event.get("matched_risk_terms", [])
    severity = drift_event.get("severity", "medium")

    # Primary relationship inferred from dominant hint
    primary_hint_rel = _HINT_TO_REL.get(hints[0]) if hints else None

    triples: list[dict[str, str]] = []

    # One triple per related entity
    for entity, role in entity_roles.items():
        if role == "monitored_client" or not entity:
            continue

        # Role → relationship, overridden by hint if it's more specific
        rel = _ROLE_TO_REL.get(role, "HAS_RISK_INDICATOR")
        if primary_hint_rel and primary_hint_rel != "HAS_RISK_INDICATOR":
            rel = primary_hint_rel  # stronger signal wins

        triples.append({"node_from": client_name, "relationship": rel, "node_to": entity})

    # For high/critical events with no entity context, add risk term triples
    if not triples and severity in ("high", "critical") and matched_terms:
        for term in matched_terms[:3]:
            triples.append({
                "node_from": client_name,
                "relationship": "HAS_RISK_INDICATOR",
                "node_to": term.replace("_", " ").title(),
            })

    return triples


# ---------------------------------------------------------------------------
# Neo4j read — fetch existing active triples for a company
# ---------------------------------------------------------------------------

def _get_existing_triples(client_name: str, driver) -> list[dict[str, str]]:
    """Return all active triples where client_name is the source node."""
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (s:Entity {name: $name})-[r]->(o:Entity)
                WHERE r.end_time IS NULL OR r.end_time = 'NA'
                RETURN s.name AS node_from, type(r) AS relationship, o.name AS node_to
                """,
                name=client_name,
            )
            return [
                {"node_from": r["node_from"], "relationship": r["relationship"], "node_to": r["node_to"]}
                for r in result
            ]
    except Exception as exc:
        print(f"[Neo4j] Failed to fetch existing triples for {client_name}: {exc}")
        return []


# ---------------------------------------------------------------------------
# Sanity checks (ported from KG-GNN-finance)
# ---------------------------------------------------------------------------

def _formal_sanity_check(
    added: list[dict], deleted: list[dict], existing: list[dict]
) -> dict[str, Any]:
    # Check 1: no triple in both added and deleted
    overlap = [t for t in added if t in deleted]
    if overlap:
        return {"correct_update": False, "reason": f"Same triple in add and delete: {overlap}"}

    # Check 2: only delete triples that actually exist in the graph
    bad_deletes = [t for t in deleted if t not in existing]
    if bad_deletes:
        return {"correct_update": False, "reason": f"Deleting non-existent triples: {bad_deletes}"}

    # Check 3: all relationship types must be in the controlled vocabulary
    bad_rels = [t for t in added + deleted if t.get("relationship") not in VALID_RELATIONSHIPS]
    if bad_rels:
        return {"correct_update": False, "reason": f"Invalid relationship types: {bad_rels}"}

    return {"correct_update": True, "reason": "All checks passed"}


# ---------------------------------------------------------------------------
# Neo4j write — additions (MERGE) and soft deletes (set end_time)
# ---------------------------------------------------------------------------

def _apply_additions(triples: list[dict[str, str]], timestamp: str, driver) -> None:
    """MERGE entity nodes and CREATE relationships with start_time."""
    with driver.session() as session:
        for t in triples:
            try:
                rel_type = t["relationship"]
                # Cypher relationship types cannot be parameterised — sanitise
                safe_rel = "".join(c for c in rel_type if c.isalnum() or c == "_").upper()
                if safe_rel not in VALID_RELATIONSHIPS:
                    continue
                session.run(
                    f"""
                    MERGE (s:Entity {{name: $from_name}})
                    MERGE (o:Entity {{name: $to_name}})
                    MERGE (s)-[r:{safe_rel}]->(o)
                    ON CREATE SET r.start_time = $ts, r.end_time = 'NA', r.state = 'ACTIVE'
                    ON MATCH SET r.state = 'ACTIVE'
                    """,
                    from_name=t["node_from"],
                    to_name=t["node_to"],
                    ts=timestamp,
                )
            except Exception as exc:
                print(f"[Neo4j] Failed to add triple {t}: {exc}")


def _apply_soft_deletes(triples: list[dict[str, str]], timestamp: str, driver) -> None:
    """Mark relationships as ended by setting end_time (preserves history)."""
    with driver.session() as session:
        for t in triples:
            try:
                safe_rel = "".join(c for c in t["relationship"] if c.isalnum() or c == "_").upper()
                session.run(
                    f"""
                    MATCH (s:Entity {{name: $from_name}})-[r:{safe_rel}]->(o:Entity {{name: $to_name}})
                    WHERE r.end_time = 'NA' OR r.end_time IS NULL
                    SET r.end_time = $ts, r.state = 'DEPRECATED'
                    """,
                    from_name=t["node_from"],
                    to_name=t["node_to"],
                    ts=timestamp,
                )
            except Exception as exc:
                print(f"[Neo4j] Failed to soft-delete triple {t}: {exc}")


# ---------------------------------------------------------------------------
# Main entry point — full KG update from a single drift event
# ---------------------------------------------------------------------------

def update_kg_from_drift_event(drift_event: dict[str, Any]) -> dict[str, Any]:
    """
    Update the Neo4j knowledge graph from a HYDRA DRIFT_EVENT.

    Implements the KG-GNN-finance update pattern:
      1. Extract candidate triples from structured drift event data
      2. Fetch existing active triples for the company from Neo4j
      3. Set diff → added / deleted / unchanged
      4. Formal sanity check (no contradictions, valid types, no phantom deletes)
      5. Apply: MERGE additions, soft-delete removed relationships
    """
    driver = _get_driver()
    if not driver:
        return {"status": "skipped", "reason": "Neo4j unavailable"}

    client_name = drift_event.get("client_name", "")
    if not client_name:
        return {"status": "skipped", "reason": "no client_name in event"}

    timestamp = drift_event.get(
        "triggered_at",
        datetime.now(timezone.utc).isoformat(),
    )

    # Step 1 — extract proposed triples
    new_triples = _extract_triples_from_drift_event(drift_event)
    if not new_triples:
        return {"status": "skipped", "reason": "no triples extracted from event"}

    # Step 2 — fetch existing active triples
    existing = _get_existing_triples(client_name, driver)

    # Step 3 — set diff
    existing_keys = {_triple_key(t) for t in existing}
    new_keys = {_triple_key(t) for t in new_triples}

    added = [t for t in new_triples if _triple_key(t) not in existing_keys]
    deleted = [t for t in existing if _triple_key(t) not in new_keys]
    unchanged = [t for t in existing if _triple_key(t) in new_keys]

    # Step 4 — formal sanity check
    check = _formal_sanity_check(added, deleted, existing)
    if not check["correct_update"]:
        print(f"[Neo4j] KG update rejected for {client_name}: {check['reason']}")
        return {"status": "rejected", "reason": check["reason"]}

    # Step 5 — apply
    _apply_additions(added, timestamp, driver)
    _apply_soft_deletes(deleted, timestamp, driver)

    result = {
        "status": "applied",
        "client": client_name,
        "added": len(added),
        "deleted": len(deleted),
        "unchanged": len(unchanged),
        "triples_added": added,
        "triples_deleted": deleted,
    }
    print(f"[Neo4j] KG updated for {client_name}: +{len(added)} -{len(deleted)} ={len(unchanged)}")
    return result


# ---------------------------------------------------------------------------
# Dashboard graph — query live nodes/edges for the network graph
# ---------------------------------------------------------------------------

def get_live_graph(company_names: list[str]) -> dict[str, Any] | None:
    """
    Query Neo4j for nodes and edges relevant to portfolio companies.
    Returns shape compatible with the frontend NetworkGraph component.
    """
    driver = _get_driver()
    if not driver:
        return None

    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (c:Entity)
                WHERE c.name IN $names
                OPTIONAL MATCH (c)-[r {state: 'ACTIVE'}]-(related:Entity)
                RETURN c, r, related
                LIMIT 300
                """,
                names=company_names,
            )

            nodes: dict[str, dict[str, Any]] = {}
            edges: list[dict[str, Any]] = []
            seen_edges: set[tuple[str, str, str]] = set()

            for record in result:
                c = record["c"]
                r = record["r"]
                related = record["related"]

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

                source_id = str(r.start_node.element_id)
                target_id = str(r.end_node.element_id)
                rel_type_name = r.type
                edge_key = (source_id, target_id, rel_type_name)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        "source": source_id,
                        "target": target_id,
                        "relationship": rel_type_name.replace("_", " ").lower(),
                    })

        return {"nodes": list(nodes.values()), "edges": edges} if nodes else None

    except Exception as exc:
        print(f"[Neo4j] Graph query failed: {exc}")
        return None


def get_active_triples(company_name: str) -> list[dict[str, Any]]:
    """Return active relationship triples for a company."""
    driver = _get_driver()
    if not driver:
        return []
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (s:Entity {name: $name})-[r]->(o:Entity)
                WHERE r.end_time IS NULL OR r.end_time = 'NA'
                RETURN s.name AS subject, type(r) AS predicate, o.name AS object,
                       r.start_time AS start_time
                LIMIT 50
                """,
                name=company_name,
            )
            return [dict(record) for record in result]
    except Exception as exc:
        print(f"[Neo4j] Triple query failed: {exc}")
        return []
