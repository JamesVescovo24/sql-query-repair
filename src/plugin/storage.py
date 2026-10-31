"""Write immutable, content-addressed reports to avoid batch collisions."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

REPORT_DIR = "reports"
MAX_REPORT_BYTES = 1_000_000


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def store(workspace: Path, payload: dict) -> tuple[str, str]:
    data = canonical(payload)
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError("report is too large")
    digest = hashlib.sha256(data).hexdigest()
    filename = f"result-{digest}.json"
    relpath = f"{REPORT_DIR}/{filename}"
    folder = workspace.resolve() / REPORT_DIR
    folder.mkdir(parents=True, exist_ok=True)
    if folder.is_symlink():
        raise ValueError("unsafe report directory")

    # Atomic replacement ensures a reader never observes a half-written file.
    # Another save may replace the same filename only with the same exact bytes.
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=folder, prefix=".result-", suffix=".tmp", delete=False) as f:
            tmp = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        destination = folder / filename
        try:
            os.replace(tmp, destination)
        except PermissionError:
            # Windows may reject replacement while another save's destination
            # is busy. An already published identical report is safe to reuse.
            if destination.is_symlink() or not destination.is_file() or destination.read_bytes() != data:
                raise
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    return relpath, digest
