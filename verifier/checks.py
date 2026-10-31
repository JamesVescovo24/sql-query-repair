"""Validate the exact immutable report named by its SHA-256 digest."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPORT_DIR = "reports"
MAX_REPORT_BYTES = 1_000_000
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def result(ok, message, **details):
    return {"valid": bool(ok), "score": 1.0 if ok else 0.0, "message": message, "details": details}


def read_receipt(workspace, output):
    digest = output.digest
    if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
        return None, "invalid report digest"
    expected_path = f"{REPORT_DIR}/result-{digest}.json"
    if output.path != expected_path:
        return None, "wrong report path"

    root = Path(workspace).resolve()
    folder = root / REPORT_DIR
    path = root / expected_path
    if folder.is_symlink() or path.is_symlink() or not path.is_file():
        return None, "report file missing or unsafe"
    if path.stat().st_size > MAX_REPORT_BYTES:
        return None, "report file exceeds size limit"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        return None, "report digest does not match file"
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        return None, "report is not valid JSON"
    if not isinstance(value, dict):
        return None, "report must be a JSON object"
    return value, None
