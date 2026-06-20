from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FEATURE_DIMENSIONS = 7
DEFAULT_MAX_SNAPSHOTS = 200


def load_nominal_snapshots(
    client_id: str,
    snapshot_dir: str | Path | None,
    max_snapshots: int = DEFAULT_MAX_SNAPSHOTS,
) -> list[list[float]]:
    if snapshot_dir is None:
        return []
    snapshot_file = _snapshot_file(snapshot_dir, client_id)
    if not snapshot_file.exists():
        return []

    snapshots: list[list[float]] = []
    for line in snapshot_file.read_text().splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        feature_vector = payload.get("feature_vector")
        if _valid_feature_vector(feature_vector):
            snapshots.append([float(value) for value in feature_vector])
    return snapshots[-max_snapshots:]


def append_nominal_snapshot(
    client_id: str,
    snapshot_dir: str | Path | None,
    feature_vector: list[float] | None,
    metadata: dict[str, Any],
    max_snapshots: int = DEFAULT_MAX_SNAPSHOTS,
) -> bool:
    if snapshot_dir is None or not _valid_feature_vector(feature_vector):
        return False

    snapshot_file = _snapshot_file(snapshot_dir, client_id)
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_raw_snapshot_lines(snapshot_file)
    payload = {
        "schema_version": "layer1.vae_snapshot.v1",
        "client_id": client_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "feature_vector": [round(float(value), 6) for value in feature_vector or []],
        "metadata": metadata,
    }
    existing.append(json.dumps(payload, sort_keys=True))
    snapshot_file.write_text("\n".join(existing[-max_snapshots:]) + "\n")
    return True


def _snapshot_file(snapshot_dir: str | Path, client_id: str) -> Path:
    safe_client_id = "".join(character if character.isalnum() or character in "-_" else "_" for character in client_id)
    return Path(snapshot_dir) / f"{safe_client_id}.jsonl"


def _load_raw_snapshot_lines(snapshot_file: Path) -> list[str]:
    if not snapshot_file.exists():
        return []
    return [line for line in snapshot_file.read_text().splitlines() if line.strip()]


def _valid_feature_vector(feature_vector: object) -> bool:
    if not isinstance(feature_vector, list) or len(feature_vector) != FEATURE_DIMENSIONS:
        return False
    return all(isinstance(value, int | float) for value in feature_vector)
