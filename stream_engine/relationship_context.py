from __future__ import annotations

import re

from backend.models import RawSignal


RELATIONSHIP_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("partnership", ("partner", "partnership", "collaboration", "alliance", "joint venture")),
    ("ownership", ("beneficial owner", "shareholder", "acquired", "acquisition", "ownership")),
    ("regulatory_investigation", ("investigation", "regulator", "lawsuit", "indictment", "fine", "penalty")),
    ("offshore_link", ("offshore", "shell company", "jurisdiction move")),
    ("business_pivot", ("pivots", "pivot", "crypto exchange", "new business model")),
)

ENTITY_PATTERN = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9&.-]*\s+){0,4}(?:AG|SA|GmbH|Ltd|Limited|Inc|Corp|Corporation|LLC|PLC)\b"
)


def extract_relationship_context(signal: RawSignal, primary_entity: str) -> dict[str, object]:
    text = signal.content
    lowered = text.lower()
    related_entities = _merge_entities(
        signal.metadata.get("related_entities", []),
        _extract_related_entities(text, primary_entity),
        primary_entity,
    )
    relationship_hints = [
        relationship
        for relationship, keywords in RELATIONSHIP_RULES
        if any(keyword in lowered for keyword in keywords)
    ]
    metadata_roles = signal.metadata.get("entity_roles", {})
    entity_roles = {primary_entity: "monitored_client"}
    for entity in related_entities:
        entity_roles[entity] = (
            metadata_roles.get(entity)
            if isinstance(metadata_roles, dict) and metadata_roles.get(entity)
            else _infer_related_entity_role(lowered)
        )

    return {
        "related_entities": related_entities,
        "relationship_hints": relationship_hints,
        "entity_roles": entity_roles,
    }


def _extract_related_entities(text: str, primary_entity: str) -> list[str]:
    candidates = []
    for match in ENTITY_PATTERN.finditer(text):
        entity = " ".join(match.group(0).split())
        if entity != primary_entity and entity not in candidates:
            candidates.append(entity)
    return candidates


def _merge_entities(metadata_entities: object, extracted_entities: list[str], primary_entity: str) -> list[str]:
    merged = []
    if isinstance(metadata_entities, list):
        for entity in metadata_entities:
            if isinstance(entity, str) and entity != primary_entity and entity not in merged:
                merged.append(entity)
    for entity in extracted_entities:
        if entity != primary_entity and entity not in merged:
            merged.append(entity)
    return merged


def _infer_related_entity_role(lowered_text: str) -> str:
    if "beneficial owner" in lowered_text or "shareholder" in lowered_text:
        return "ownership_related_entity"
    if "offshore" in lowered_text or "shell company" in lowered_text:
        return "structural_risk_related_entity"
    if "partner" in lowered_text or "partnership" in lowered_text:
        return "partner_or_counterparty"
    if "investigation" in lowered_text or "regulator" in lowered_text:
        return "investigation_related_entity"
    return "mentioned_related_entity"
