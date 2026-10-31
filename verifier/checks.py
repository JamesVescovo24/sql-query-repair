"""Pure deterministic report checks. No plugin imports, LLM, network or subprocesses."""
import hashlib
import json
from pathlib import Path

REPORT_PATH = "reports/result.json"

def result(ok, message, **details):
    return {"valid": bool(ok), "score": 1.0 if ok else 0.0, "message": message, "details": details}

def read_receipt(workspace, output):
    if output.path != REPORT_PATH:
        return None, "wrong report path"
    path = Path(workspace) / REPORT_PATH
    if path.is_symlink() or not path.is_file():
        return None, "report file missing or unsafe"
    if path.stat().st_size > 1_000_000:
        return None, "report file exceeds size limit"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != output.digest:
        return None, "report digest does not match file"
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        return None, "report is not valid JSON"
    if not isinstance(value, dict):
        return None, "report must be a JSON object"
    return value, None
