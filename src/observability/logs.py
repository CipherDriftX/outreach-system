"""Structured logging for Outreach OS."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def write_node_logs(run_id: str, entries: list[dict]) -> None:
    path = LOG_DIR / f"run_{run_id}.jsonl"
    with open(path, "a") as f:
        for entry in entries:
            entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            f.write(json.dumps(entry, default=str) + "\n")