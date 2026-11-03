#!/usr/bin/env python3
"""Validate registered capture evidence and emit a conservative corpus status.

The evaluator validates files, hashes, metadata, and artifact references. It does
not rerun reference tools, infer a limitation, or invent experimental values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "captures" / "manifest.json"
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _inside_repo(relative_path: str, description: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError(f"{description} must be a non-empty repository-relative path")
    path = (ROOT / relative_path).resolve()
    if ROOT.resolve() not in path.parents:
        raise ValueError(f"{description} must stay inside repository")
    if not path.is_file():
        raise ValueError(f"{description} does not exist: {relative_path}")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_metadata(entry: dict, capture_id: str, capture_path: Path) -> dict | None:
    metadata_ref = entry.get("metadata_file")
    if metadata_ref is None:
        return None
    metadata_path = _inside_repo(metadata_ref, f"{capture_id}: metadata_file")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{capture_id}: invalid metadata JSON: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ValueError(f"{capture_id}: metadata must be a JSON object")
    recorded_id = metadata.get("id", metadata.get("capture_id"))
    if recorded_id is not None and recorded_id != capture_id:
        raise ValueError(f"{capture_id}: metadata ID mismatch: {recorded_id}")
    recorded_capture = metadata.get("capture", metadata.get("capture_file"))
    if recorded_capture is not None:
        metadata_capture_path = (ROOT / recorded_capture).resolve()
        if metadata_capture_path != capture_path:
            raise ValueError(f"{capture_id}: metadata capture path does not match manifest")
    return metadata


def _validate_artifact_paths(entry: dict, capture_id: str) -> None:
    artifacts = entry.get("evidence_files", [])
    if not isinstance(artifacts, list) or any(not isinstance(item, str) for item in artifacts):
        raise ValueError(f"{capture_id}: evidence_files must be a list of paths")
    for artifact in artifacts:
        _inside_repo(artifact, f"{capture_id}: evidence artifact")

    outputs = entry.get("baseline_outputs", {})
    if not isinstance(outputs, dict) or any(not isinstance(item, str) for item in outputs.values()):
        raise ValueError(f"{capture_id}: baseline_outputs must map names to paths")
    for artifact in outputs.values():
        _inside_repo(artifact, f"{capture_id}: baseline output")


def load_manifest(path: Path = MANIFEST) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise ValueError("manifest must be an object with schema_version: 1")
    captures = doc.get("captures")
    if not isinstance(captures, list):
        raise ValueError("manifest captures must be a list")

    seen: set[str] = set()
    for index, entry in enumerate(captures):
        if not isinstance(entry, dict):
            raise ValueError(f"captures[{index}] must be an object")
        capture_id = entry.get("capture_id")
        if not isinstance(capture_id, str) or not capture_id:
            raise ValueError(f"captures[{index}] needs a non-empty capture_id")
        if capture_id in seen:
            raise ValueError(f"duplicate capture_id: {capture_id}")
        seen.add(capture_id)

        capture_path = _inside_repo(entry.get("capture_file"), f"{capture_id}: capture_file")
        commands = entry.get("commands", [])
        if not isinstance(commands, list) or any(not isinstance(command, str) for command in commands):
            raise ValueError(f"{capture_id}: commands must be a list of strings")
        expected = entry.get("expected_properties", [])
        if not isinstance(expected, list):
            raise ValueError(f"{capture_id}: expected_properties must be a list")

        metadata = _read_metadata(entry, capture_id, capture_path)
        expected_hash = entry.get("sha256")
        if expected_hash is None and metadata:
            expected_hash = metadata.get("sha256")
        if expected_hash is not None:
            if not isinstance(expected_hash, str) or not _SHA256.fullmatch(expected_hash):
                raise ValueError(f"{capture_id}: sha256 must be 64 hexadecimal characters")
            actual_hash = sha256_file(capture_path)
            if actual_hash.lower() != expected_hash.lower():
                raise ValueError(f"{capture_id}: capture SHA-256 mismatch (expected {expected_hash}, got {actual_hash})")
            if metadata and metadata.get("sha256") and metadata["sha256"].lower() != actual_hash.lower():
                raise ValueError(f"{capture_id}: metadata SHA-256 does not match capture")

        hash_file = entry.get("capture_hash_file")
        if hash_file is not None:
            path_to_hash = _inside_repo(hash_file, f"{capture_id}: capture_hash_file")
            if expected_hash is None:
                raise ValueError(f"{capture_id}: capture_hash_file requires a recorded SHA-256")
            values = path_to_hash.read_text(encoding="utf-8").split()
            if not values or values[0].lower() != expected_hash.lower():
                raise ValueError(f"{capture_id}: capture_hash_file disagrees with manifest SHA-256")

        _validate_artifact_paths(entry, capture_id)
        status = entry.get("provenance_status", "unclassified")
        if status not in {"provisional", "complete", "unclassified"}:
            raise ValueError(f"{capture_id}: unsupported provenance_status: {status}")
        missing = entry.get("missing_provenance", [])
        if not isinstance(missing, list) or any(not isinstance(item, str) for item in missing):
            raise ValueError(f"{capture_id}: missing_provenance must be a list of strings")
        capture_status = entry.get("capture_status", "unknown")
        packet_count = entry.get("packet_count")
        if capture_status not in {"captured", "empty", "unknown"}:
            raise ValueError(f"{capture_id}: unsupported capture_status: {capture_status}")
        if packet_count is not None and (not isinstance(packet_count, int) or packet_count < 0):
            raise ValueError(f"{capture_id}: packet_count must be a non-negative integer")
        if capture_status == "captured" and packet_count == 0:
            raise ValueError(f"{capture_id}: captured status conflicts with zero packets")
        if capture_status == "empty" and packet_count != 0:
            raise ValueError(f"{capture_id}: empty status requires packet_count: 0")
    return doc


def summarize(manifest: dict) -> dict:
    captures = manifest["captures"]
    statuses = [entry.get("provenance_status", "unclassified") for entry in captures]
    provisional = sum(status == "provisional" for status in statuses)
    complete = sum(status == "complete" for status in statuses)
    unclassified = sum(status == "unclassified" for status in statuses)
    captures_with_packets = sum(entry.get("capture_status") == "captured" for entry in captures)
    empty_captures = sum(entry.get("capture_status") == "empty" for entry in captures)
    unknown_packet_status = sum(entry.get("capture_status", "unknown") == "unknown" for entry in captures)
    if not captures:
        status = "no_evidence_yet"
        note = "No capture records are present; no experimental result is claimed."
    elif provisional or unclassified:
        status = "provisional_evidence"
        note = "Capture artifacts and hashes validate, but provisional provenance remains open; no limitation conclusion is inferred."
    else:
        status = "evidence_registered"
        note = "Capture records validate; this status alone does not establish a limitation or research conclusion."
    return {
        "schema_version": 1,
        "capture_count": len(captures),
        "validated_capture_count": len(captures),
        "provisional_capture_count": provisional,
        "complete_provenance_count": complete,
        "unclassified_capture_count": unclassified,
        "captures_with_packets": captures_with_packets,
        "empty_capture_count": empty_captures,
        "unknown_packet_status_count": unknown_packet_status,
        "status": status,
        "captures": [
            {
                "capture_id": entry["capture_id"],
                "scenario": entry.get("scenario"),
                "provenance_status": entry.get("provenance_status", "unclassified"),
                "sha256": entry.get("sha256"),
                "capture_status": entry.get("capture_status", "unknown"),
                "packet_count": entry.get("packet_count"),
                "missing_provenance": entry.get("missing_provenance", []),
            }
            for entry in captures
        ],
        "note": note,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        summary = summarize(load_manifest())
    except ValueError as exc:
        print(f"manifest error: {exc}", file=sys.stderr)
        return 1
    if args.check_only:
        print(
            "manifest valid: "
            f"{summary['capture_count']} capture(s) "
            f"({summary['captures_with_packets']} with packets, "
            f"{summary['empty_capture_count']} empty, "
            f"{summary['provisional_capture_count']} provisional)"
        )
        return 0
    output = args.output or ROOT / "results" / "evaluation.json"
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output.relative_to(ROOT) if ROOT in output.parents else output}")
    print(f"status: {summary['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
