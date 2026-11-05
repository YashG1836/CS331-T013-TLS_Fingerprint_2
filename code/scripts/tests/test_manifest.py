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
    assert result["capture_count"] == 16
    assert result["validated_capture_count"] == 16
    assert result["captures_with_packets"] == 15
    assert result["empty_capture_count"] == 1
    assert result["provisional_capture_count"] == 16
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



def test_track1_capture_set_and_empty_ipv6_are_registered_explicitly():
    manifest = load_manifest()
    entries = {entry["capture_id"]: entry for entry in manifest["captures"]}
    expected = {
        "quic_chromium", "quic_curl", "tls_keylog_curl", "tls_offload_on",
        "tls_offload_off", "tls_pq_on", "tls_pq_off", "tls_chromium_repeat",
        "tls_curl_repeat", "tls_python_repeat", "tls_ipv4", "tls_ipv6",
        "tls_ech_off", "tls_ech_on", "tls_ech_doh",
    }
    assert expected <= entries.keys()
    assert all(entries[capture_id]["provenance_status"] == "provisional" for capture_id in expected)
    ipv6 = entries["tls_ipv6"]
    assert ipv6["capture_status"] == "empty"
    assert ipv6["packet_count"] == 0
    assert ipv6["observations"]["tools_agree"] is None


def test_imported_chromium_repeat_result_records_released_vs_main_ja4():
    summary = json.loads((ROOT / "results/summary.json").read_text())
    row = next(item for item in summary if item["id"] == "tls_chromium_repeat")
    assert row["hellos_tshark"] == 50
    assert row["distinct_ja4"] == 15
    assert row["distinct_ja4_main"] == 1


def test_imported_raw_outputs_match_nonempty_summary_counts():
    summary = json.loads((ROOT / "results/summary.json").read_text())
    for row in summary:
        raw = json.loads((ROOT / "results/raw" / f"{row['id']}.json").read_text())
        hellos = raw["tshark_client_hellos"]
        foxio = raw["foxio_ja4"]
        assert len(hellos) == row["hellos_tshark"]
        assert sum("ja4" in result for result in foxio) == row["hellos_ja4"]
        tshark_ja4 = {item.get("tls.handshake.ja4") for item in hellos} - {None, ""}
        foxio_ja4 = {item.get("ja4") for item in foxio} - {None, ""}
        assert len(tshark_ja4) == row["distinct_ja4"]
        if not tshark_ja4 or not foxio_ja4:
            assert row["tools_agree"] is None
        else:
            assert (tshark_ja4 == foxio_ja4) is row["tools_agree"]


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
