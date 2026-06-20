from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

DB_PATH = Path("data/db.json")


def _load() -> dict[str, Any]:
    if not DB_PATH.exists():
        return {"alerts": {}, "actions": [], "pipeline_runs": []}
    return json.loads(DB_PATH.read_text())


def _save(data: dict[str, Any]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(data, indent=2, default=str))


def upsert_alert(alert: dict[str, Any]) -> None:
    data = _load()
    data["alerts"][alert["id"]] = alert
    _save(data)


def get_alert(alert_id: str) -> dict[str, Any] | None:
    return _load()["alerts"].get(alert_id)


def get_all_alerts() -> list[dict[str, Any]]:
    return list(_load()["alerts"].values())


def record_action(alert_id: str, action: str, actor: str, note: str = "") -> dict[str, Any]:
    data = _load()
    record = {
        "id": str(uuid.uuid4()),
        "alert_id": alert_id,
        "action": action,
        "actor": actor,
        "note": note,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    data["actions"].append(record)
    if alert_id in data["alerts"]:
        status_map = {"approve": "reviewed", "escalate": "investigating", "dismiss": "dismissed"}
        data["alerts"][alert_id]["status"] = status_map.get(action, action)
    _save(data)
    return record


def get_audit_log() -> list[dict[str, Any]]:
    return _load()["actions"]


def record_pipeline_run(result: dict[str, Any]) -> None:
    data = _load()
    data["pipeline_runs"].append({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **result,
    })
    _save(data)
