#!/usr/bin/env python3
"""Run the pinned reference tools on one registered, reviewed capture.

This records tool output; it does not interpret results, compare fingerprints,
or assert that any limitation has been observed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence

from evaluate import ROOT, load_manifest
from preflight import FINGERPRINT_FIELDS, parse_tshark_fields

VERSION = 1
DEFAULT_TIMEOUT = 180


def find_capture(capture_id: str) -> tuple[dict, Path]:
    manifest = load_manifest()
    matches = [entry for entry in manifest["captures"] if entry["capture_id"] == capture_id]
    if not matches:
        raise ValueError(f"capture_id is not registered in captures/manifest.json: {capture_id}")
    entry = matches[0]
    path = (ROOT / entry["capture_file"]).resolve()
    if ROOT.resolve() not in path.parents:
        raise ValueError("capture path must stay inside the repository")
    if not path.is_file():
        raise ValueError(f"registered capture does not exist: {entry['capture_file']}")
    return entry, path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def invoke(argv: Sequence[str], timeout: int = DEFAULT_TIMEOUT) -> dict:
    executable = shutil.which(argv[0]) if not Path(argv[0]).is_absolute() else argv[0]
    if executable is None or not Path(executable).is_file():
        return {"argv": list(argv), "available": False, "error": f"executable not found: {argv[0]}"}
    command = [executable, *argv[1:]]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"argv": command, "available": True, "error": str(exc)}
    return {
        "argv": command,
        "available": True,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def select_tshark_fields(available: set[str]) -> list[str]:
    candidates = (
        "frame.number", "frame.time_epoch", "ip.src", "ip.dst", "ipv6.src", "ipv6.dst",
        "udp.stream", "udp.srcport", "udp.dstport", "quic.version", "quic.dcid",
        "quic.long.packet_type", "tls.handshake.type", *FINGERPRINT_FIELDS,
    )
    return [field for field in candidates if field in available]


def parse_tshark_rows(text: str) -> list[dict[str, str]]:
    if not text.strip():
        return []
    return [dict(row) for row in csv.DictReader(io.StringIO(text), delimiter="\t")]


def run_capture_baseline(
    capture_id: str,
    capture_path: Path,
    *,
    ja4_executable: str = "ja4",
    tshark_executable: str = "tshark",
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Capture command/version/output metadata for JA4+ and TShark."""
    capture_path = capture_path.resolve()
    ja4_version = invoke((ja4_executable, "--version"), timeout)
    tshark_version = invoke((tshark_executable, "--version"), timeout)
    tshark_field_listing = invoke((tshark_executable, "-G", "fields"), timeout)

    fields: set[str] = set()
    if tshark_field_listing.get("exit_code") == 0:
        fields = parse_tshark_fields(tshark_field_listing.get("stdout", ""))
    selected_fields = select_tshark_fields(fields)

    ja4_result = invoke((ja4_executable, "--json", str(capture_path)), timeout)
    tshark_result = None
    if selected_fields:
        tshark_result = invoke(
            (tshark_executable, "-r", str(capture_path), "-T", "fields",
             "-E", "header=y", "-E", "separator=/t", "-E", "quote=d",
             *[argument for field in selected_fields for argument in ("-e", field)]),
            timeout,
        )

    ja4_output = ja4_result.get("stdout", "")
    try:
        parsed_ja4_output = json.loads(ja4_output) if ja4_output else None
    except json.JSONDecodeError:
        parsed_ja4_output = None

    tshark_output = (tshark_result or {}).get("stdout", "")
    statuses = (ja4_version, tshark_version, tshark_field_listing, ja4_result)
    if tshark_result is not None:
        statuses = (*statuses, tshark_result)
    else:
        statuses = (*statuses, {"available": False, "error": "TShark exposed no supported fields"})
    complete = all(item.get("available") and item.get("exit_code") == 0 for item in statuses)
    return {
        "schema_version": VERSION,
        "capture_id": capture_id,
        "capture_file": capture_path.relative_to(ROOT).as_posix()
        if ROOT.resolve() in capture_path.parents else str(capture_path),
        "capture_sha256": sha256_file(capture_path),
        "status": "commands_completed" if complete else "tool_or_command_failure",
        "interpretation": "Raw reference outputs only; no fingerprint comparison or limitation result is inferred.",
        "tools": {
            "ja4_plus": {
                "version_command": ja4_version,
                "capture_command": ja4_result,
                "parsed_json": parsed_ja4_output,
            },
            "tshark": {
                "version_command": tshark_version,
                "field_listing_command": tshark_field_listing,
                "available_fields": sorted(fields),
                "fingerprint_fields_available": {field: field in fields for field in FINGERPRINT_FIELDS},
                "selected_fields": selected_fields,
                "capture_command": tshark_result,
                "parsed_rows": parse_tshark_rows(tshark_output) if tshark_result and tshark_result.get("exit_code") == 0 else [],
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-id", required=True, help="ID registered in captures/manifest.json")
    parser.add_argument("--output", type=Path, help="JSON output path; defaults to results/reference/<capture-id>.json")
    parser.add_argument("--ja4", default="ja4", help="FoxIO JA4+ executable (default: ja4)")
    parser.add_argument("--tshark", default="tshark", help="TShark executable (default: tshark)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    try:
        _entry, capture_path = find_capture(args.capture_id)
        report = run_capture_baseline(args.capture_id, capture_path,
                                      ja4_executable=args.ja4,
                                      tshark_executable=args.tshark,
                                      timeout=args.timeout)
    except (OSError, ValueError) as exc:
        print(f"baseline error: {exc}", file=sys.stderr)
        return 1

    output = args.output or ROOT / "results" / "reference" / f"{args.capture_id}.json"
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    print(f"status: {report['status']}")
    return 0 if report["status"] == "commands_completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
