"""Regression tests for independent and concurrent report saves."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from types import SimpleNamespace

import pytest

from plugin.storage import store
from verifier.checks import read_receipt


def test_two_reports_remain_valid_in_same_workspace(tmp_path):
    # Originally all saves overwrote reports/result.json, invalidating old receipts.
    first = {"batch": "first", "rows": [1]}
    second = {"batch": "second", "rows": [2]}
    p1, d1 = store(tmp_path, first)
    p2, d2 = store(tmp_path, second)
    assert p1 != p2
    assert read_receipt(tmp_path, SimpleNamespace(path=p1, digest=d1)) == (first, None)
    assert read_receipt(tmp_path, SimpleNamespace(path=p2, digest=d2)) == (second, None)


def test_concurrent_saves_do_not_clobber(tmp_path):
    payloads = [{"batch": f"batch-{i}", "index": i} for i in range(12)]
    with ThreadPoolExecutor(max_workers=6) as executor:
        receipts = list(executor.map(lambda payload: store(tmp_path, payload), payloads))
    for payload, (path, digest) in zip(payloads, receipts):
        assert read_receipt(tmp_path, SimpleNamespace(path=path, digest=digest)) == (payload, None)


def test_forged_paths_and_corrupt_files_are_rejected(tmp_path):
    path, digest = store(tmp_path, {"okay": True})
    assert read_receipt(tmp_path, SimpleNamespace(path="../elsewhere.json", digest=digest))[0] is None
    assert read_receipt(tmp_path, SimpleNamespace(path=path, digest="bad"))[0] is None
    (tmp_path / path).write_text('{corrupted', encoding="utf-8")
    saved, reason = read_receipt(tmp_path, SimpleNamespace(path=path, digest=digest))
    assert saved is None
    assert reason == "report digest does not match file"


def test_malformed_json_with_correct_digest_is_rejected(tmp_path):
    malformed = b"{not valid json"
    digest = hashlib.sha256(malformed).hexdigest()
    path = f"reports/result-{digest}.json"
    (tmp_path / "reports").mkdir()
    (tmp_path / path).write_bytes(malformed)
    saved, problem = read_receipt(tmp_path, SimpleNamespace(path=path, digest=digest))
    assert saved is None
    assert problem == "report is not valid JSON"


def test_identical_concurrent_saves_return_same_receipt(tmp_path):
    payload = {"batch": "same", "rows": [1, 2, 3]}
    with ThreadPoolExecutor(max_workers=6) as executor:
        receipts = list(executor.map(lambda _: store(tmp_path, payload), range(12)))
    assert len(set(receipts)) == 1
    path, digest = receipts[0]
    assert path == f"reports/result-{digest}.json"
    assert read_receipt(tmp_path, SimpleNamespace(path=path, digest=digest)) == (payload, None)
    assert list((tmp_path / "reports").iterdir()) == [tmp_path / path]


def test_replace_permission_error_only_reuses_identical_report(tmp_path, monkeypatch):
    payload = {"okay": True}
    path, digest = store(tmp_path, payload)

    def deny_replace(*args):
        raise PermissionError("destination is busy")

    monkeypatch.setattr("plugin.storage.os.replace", deny_replace)
    assert store(tmp_path, payload) == (path, digest)
    with pytest.raises(PermissionError):
        store(tmp_path, {"different": True})
    (tmp_path / path).write_bytes(b"tampered")
    with pytest.raises(PermissionError):
        store(tmp_path, payload)
    assert (tmp_path / path).read_bytes() == b"tampered"
    assert list((tmp_path / "reports").iterdir()) == [tmp_path / path]
