import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import ROOT, load_manifest


def test_committed_manifest_is_valid():
    assert load_manifest()["schema_version"] == 1


def test_missing_capture_is_rejected(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "captures": [{
        "capture_id": "missing", "capture_file": "captures/not-there.pcap"
    }]}), encoding="utf-8")
    with pytest.raises(ValueError, match="does not exist"):
        load_manifest(manifest)


def test_duplicate_capture_ids_are_rejected(tmp_path: Path):
    capture = ROOT / "README.md"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "captures": [
        {"capture_id": "same", "capture_file": str(capture.relative_to(ROOT))},
        {"capture_id": "same", "capture_file": str(capture.relative_to(ROOT))},
    ]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate capture_id"):
        load_manifest(manifest)


def test_path_escape_is_rejected(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "captures": [{
        "capture_id": "escape", "capture_file": "../../etc/passwd"
    }]}), encoding="utf-8")
    with pytest.raises(ValueError, match="stay inside"):
        load_manifest(manifest)
