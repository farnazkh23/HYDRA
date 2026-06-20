from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def append_layer1_audit_record(
    audit_log_dir: str | Path | None,
    client_id: str,
    record: dict[str, Any],
) -> bool:
    if audit_log_dir is None:
        return False
    audit_file = _audit_file(audit_log_dir, client_id)
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "layer1.audit.v1",
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "client_id": client_id,
        **record,
    }
    with audit_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, sort_keys=True) + "\n")
    return True


def _audit_file(audit_log_dir: str | Path, client_id: str) -> Path:
    safe_client_id = "".join(character if character.isalnum() or character in "-_" else "_" for character in client_id)
    return Path(audit_log_dir) / f"{safe_client_id}.jsonl"
