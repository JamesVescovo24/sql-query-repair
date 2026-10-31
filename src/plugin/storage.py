"""Minimal, bounded JSON artifact writer (actual output is checked by verifier)."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

REPORT_PATH = "reports/result.json"

def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")

def store(workspace: Path, payload: dict) -> tuple[str, str]:
    root = workspace.resolve()
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical(payload)
    if len(data) > 1_000_000:
        raise ValueError("report is too large")
    path.write_bytes(data)
    return REPORT_PATH, hashlib.sha256(data).hexdigest()
