import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import evaluate
from evaluate import ROOT, load_manifest, summarize


def _temporary_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(evaluate, "ROOT", root)
    return root


def test_committed_manifest_is_valid_and_provisional():
    manifest = load_manifest()
    result = summarize(manifest)
    assert manifest["schema_version"] == 1
    assert result["capture_count"] == 1
    assert result["validated_capture_count"] == 1
    assert result["provisional_capture_count"] == 1
    assert result["complete_provenance_count"] == 0
    assert result["status"] == "provisional_evidence"
    assert "no limitation conclusion is inferred" in result["note"]


def test_registered_reference_outputs_agree_for_client_hello():
    entry = load_manifest()["captures"][0]
    foxio = json.loads((ROOT / entry["baseline_outputs"]["foxio_ja4"]).read_text())
    with (ROOT / entry["baseline_outputs"]["tshark_fields"]).open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    client_hello_rows = [row for row in rows if row.get("tls.handshake.type") == "1"]
    assert len(client_hello_rows) == 1
    assert foxio["ja4"] == client_hello_rows[0]["tls.handshake.ja4"]
    assert foxio["ja4"] == entry["observations"]["foxio_ja4"]
    assert client_hello_rows[0]["tls.handshake.ja3"] == entry["observations"]["tshark_ja3"]


def test_missing_capture_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _temporary_root(tmp_path, monkeypatch)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "captures": [{
        "capture_id": "missing", "capture_file": "captures/not-there.pcap"
    }]}), encoding="utf-8")
    with pytest.raises(ValueError, match="does not exist"):
        load_manifest(manifest)


def test_duplicate_capture_ids_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _temporary_root(tmp_path, monkeypatch)
    (root / "capture.pcap").write_bytes(b"pcap")
    manifest = tmp_path / "manifest.json"
    capture_entry = {"capture_id": "same", "capture_file": "capture.pcap"}
    manifest.write_text(json.dumps({"schema_version": 1, "captures": [capture_entry, capture_entry]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate capture_id"):
        load_manifest(manifest)


def test_path_escape_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _temporary_root(tmp_path, monkeypatch)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "captures": [{
        "capture_id": "escape", "capture_file": "../../etc/passwd"
    }]}), encoding="utf-8")
    with pytest.raises(ValueError, match="stay inside"):
        load_manifest(manifest)


def test_capture_sha256_mismatch_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _temporary_root(tmp_path, monkeypatch)
    (root / "capture.pcap").write_bytes(b"real capture bytes")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "captures": [{
        "capture_id": "bad-hash", "capture_file": "capture.pcap", "sha256": "0" * 64
    }]}), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_manifest(manifest)


def test_metadata_capture_path_and_hash_must_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _temporary_root(tmp_path, monkeypatch)
    capture = root / "capture.pcap"
    capture.write_bytes(b"real capture bytes")
    metadata = root / "metadata.json"
    metadata.write_text(json.dumps({
        "id": "metadata-case", "capture": "other.pcap", "sha256": "0" * 64
    }), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "captures": [{
        "capture_id": "metadata-case", "capture_file": "capture.pcap",
        "metadata_file": "metadata.json", "sha256": "0" * 64
    }]}), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata capture path"):
        load_manifest(manifest)
