from __future__ import annotations

import json
from pathlib import Path

from backend.models import Layer1KycBaseline


DEFAULT_PROFILE_PATH = Path(__file__).with_name("profiles.json")


def load_layer1_baselines(path: str | Path = DEFAULT_PROFILE_PATH) -> dict[str, Layer1KycBaseline]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    baselines = [Layer1KycBaseline(**client) for client in payload["clients"]]
    return {baseline.client_id: baseline for baseline in baselines}
