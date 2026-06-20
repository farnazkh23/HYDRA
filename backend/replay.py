from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from backend.models import RawSignal, SignalType


def model_to_json_dict(model: object) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")  # type: ignore[attr-defined]
    if hasattr(model, "json"):
        return json.loads(model.json())  # type: ignore[attr-defined]
    raise TypeError(f"Unsupported model type: {type(model)!r}")


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            file.write("\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    input_path = Path(path)
    if not input_path.exists():
        return []
    records = []
    with input_path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def write_raw_signals(path: str | Path, signals: Iterable[RawSignal]) -> None:
    write_jsonl(path, (model_to_json_dict(signal) for signal in signals))


def load_raw_signals(path: str | Path, client_id: str | None = None) -> list[RawSignal]:
    signals = [_raw_signal_from_dict(record) for record in read_jsonl(path)]
    if client_id is None:
        return signals
    return [signal for signal in signals if signal.client_id == client_id]


def _raw_signal_from_dict(record: dict[str, Any]) -> RawSignal:
    timestamp = record.get("timestamp")
    if isinstance(timestamp, str):
        record = {**record, "timestamp": _parse_datetime(timestamp)}
    signal_type = record.get("signal_type")
    if isinstance(signal_type, str):
        record = {**record, "signal_type": SignalType(signal_type)}
    return RawSignal(**record)


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
