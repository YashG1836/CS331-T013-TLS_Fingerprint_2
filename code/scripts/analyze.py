#!/usr/bin/env python3
"""Re-run TShark and FoxIO against the registered Track 1 PCAPs.

By default all output is written below results/reproduced/; imported evidence
under results/raw/ and results/summary.* is never overwritten.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

from evaluate import ROOT, load_manifest

HELLO_FIELDS = [
    "frame.number", "tls.handshake.extensions_server_name", "tls.handshake.ja3",
    "tls.handshake.ja4", "tls.handshake.length", "tcp.segment.count",
    "quic.crypto.fragment.count", "tls.ech.client_hello_type",
]
SERVER_FIELDS = ["frame.number", "tls.handshake.extensions_key_share_group"]
TABLE_COLUMNS = [
    "id", "limitation", "capture_status", "hellos_tshark", "hellos_ja4",
    "distinct_ja3", "distinct_ja4", "distinct_ja4_main", "tools_agree",
    "ja4x_ja4h_no_keys", "ja4x_ja4h_with_keys", "hello_bytes_max",
    "pieces_max", "biggest_frame", "groups_chosen", "ech_ext_hellos",
    "seconds_tshark", "seconds_ja4",
]


def run(argv: Sequence[str], timeout: int = 180) -> dict[str, Any]:
    """Run a tool without hiding missing executables, exit codes, or stderr."""
    executable = shutil.which(argv[0]) if argv else None
    if executable is None:
        return {"argv": list(argv), "available": False, "error": f"executable not found: {argv[0] if argv else ''}"}
    command = [executable, *argv[1:]]
    started = time.monotonic()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "argv": command,
            "available": True,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "seconds": round(time.monotonic() - started, 3),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "argv": command,
            "available": True,
            "error": str(exc),
            "seconds": round(time.monotonic() - started, 3),
        }


def numbers(values: Sequence[str]) -> list[int]:
    """Convert comma-separated decimal TShark values to integers."""
    result: list[int] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part.isdigit():
                result.append(int(part))
    return result


def _tshark_fields(listing: dict[str, Any]) -> set[str]:
    if listing.get("exit_code") != 0:
        return set()
    fields: set[str] = set()
    for line in listing.get("stdout", "").splitlines():
        cols = line.split("\t")
        if len(cols) >= 3 and cols[0] == "F":
            fields.add(cols[2])
    return fields


def _rows(result: dict[str, Any]) -> list[dict[str, str]]:
    if result.get("exit_code") != 0:
        return []
    text = result.get("stdout", "")
    if not text.strip():
        return []
    return [dict(row) for row in csv.DictReader(io.StringIO(text), delimiter="\t")]


def _field_query(tshark: str, pcap: Path, display_filter: str,
                 requested: Sequence[str], available: set[str], timeout: int) -> dict[str, Any]:
    fields = [field for field in requested if field in available]
    if not fields:
        return {"argv": [], "available": True, "exit_code": 2,
                "error": "none of the requested fields are registered by this TShark"}
    return run((tshark, "-r", str(pcap), "-Y", display_filter, "-T", "fields",
                "-E", "header=y", "-E", "separator=/t", "-E", "quote=d",
                *[arg for field in fields for arg in ("-e", field)]), timeout)


def _json_lines(text: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                decoded = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                values.append(decoded)
    return values


def _count_nested_keys(value: Any, wanted: set[str]) -> int:
    if isinstance(value, dict):
        return sum((1 if key in wanted else 0) + _count_nested_keys(child, wanted)
                   for key, child in value.items())
    if isinstance(value, list):
        return sum(_count_nested_keys(item, wanted) for item in value)
    return 0


def _capture_analysis(entry: dict, settings: dict, *, tshark: str, ja4: str,
                      ja4_main: str, timeout: int) -> tuple[dict, dict]:
    capture_path = (ROOT / entry["capture_file"]).resolve()
    listing = run((tshark, "-G", "fields"), timeout)
    available_fields = _tshark_fields(listing)
    hello_result = _field_query(tshark, capture_path, "tls.handshake.type == 1",
                                HELLO_FIELDS, available_fields, timeout)
    server_result = _field_query(tshark, capture_path, "tls.handshake.type == 2",
                                 SERVER_FIELDS, available_fields, timeout)
    frame_result = _field_query(tshark, capture_path, "frame", ["frame.len"], available_fields, timeout)
    dns_result = _field_query(tshark, capture_path, "dns.flags.response == 0",
                              ["dns.qry.name"], available_fields, timeout)
    hello_rows, server_rows = _rows(hello_result), _rows(server_result)
    frame_rows, dns_rows = _rows(frame_result), _rows(dns_result)

    ja4_result = run((ja4, "--json", "--with-raw", str(capture_path)), timeout)
    ja4_values = _json_lines(ja4_result.get("stdout", ""))
    main_result = run((ja4_main, "--json", "--with-raw", str(capture_path)), timeout) if ja4_main else {
        "argv": [], "available": False, "error": "optional ja4-main executable not configured"
    }
    main_values = _json_lines(main_result.get("stdout", ""))

    keylog_result = None
    recipe = entry.get("capture_recipe", {})
    keylog_path = ROOT / settings.get("keylog_dir", "captures/keylogs") / f"{entry['capture_id']}.keylog"
    if recipe.get("keylog") and keylog_path.is_file():
        keylog_result = run((ja4, "--json", "--with-raw", str(capture_path),
                             "--keylog-file", str(keylog_path)), timeout)
        keylog_values = _json_lines(keylog_result.get("stdout", ""))
    else:
        keylog_values = []

    ja4_tshark = {row.get("tls.handshake.ja4", "") for row in hello_rows} - {""}
    ja4_foxio = {obj.get("ja4", "") for obj in ja4_values} - {""}
    ja4_main_set = {obj.get("ja4", "") for obj in main_values} - {""}
    values_available = bool(hello_rows and ja4_values and ja4_tshark and ja4_foxio)
    agreement = (ja4_tshark == ja4_foxio) if values_available else None
    pieces = numbers([row.get("tcp.segment.count", "") for row in hello_rows]
                     + [row.get("quic.crypto.fragment.count", "") for row in hello_rows])
    row = {
        "id": entry["capture_id"],
        "limitation": entry.get("limitation", ""),
        "capture_status": entry.get("capture_status", "unknown"),
        "packet_count": entry.get("packet_count"),
        "hellos_tshark": len(hello_rows),
        "hellos_ja4": sum("ja4" in obj for obj in ja4_values),
        "distinct_ja3": len({r.get("tls.handshake.ja3", "") for r in hello_rows} - {""}),
        "distinct_ja4": len(ja4_tshark),
        "distinct_ja4_main": len(ja4_main_set) if main_result.get("exit_code") == 0 else None,
        "tools_agree": agreement,
        "ja4x_ja4h_no_keys": _count_nested_keys(ja4_values, {"ja4x", "ja4h"}),
        "ja4x_ja4h_with_keys": _count_nested_keys(keylog_values, {"ja4x", "ja4h"}) if keylog_result else None,
        "hello_bytes_max": max(numbers([r.get("tls.handshake.length", "") for r in hello_rows]), default=0),
        "pieces_max": max(pieces, default=None),
        "biggest_frame": max(numbers([r.get("frame.len", "") for r in frame_rows]), default=None),
        "groups_chosen": sorted(set(numbers([r.get("tls.handshake.extensions_key_share_group", "") for r in server_rows]))),
        "ech_ext_hellos": sum(r.get("tls.ech.client_hello_type", "") != "" for r in hello_rows),
        "seconds_tshark": round(sum(x.get("seconds", 0) for x in [hello_result, server_result, frame_result, dns_result]), 3),
        "seconds_ja4": ja4_result.get("seconds"),
        "tool_errors": [x.get("error", x.get("stderr", "")) for x in
                        [hello_result, server_result, frame_result, dns_result, ja4_result]
                        if x.get("error") or (x.get("exit_code") not in (None, 0))],
    }
    raw = {
        "capture_id": entry["capture_id"],
        "capture_sha256": entry.get("sha256"),
        "tshark_field_listing": listing,
        "tshark_client_hellos": {"command": hello_result, "rows": hello_rows},
        "tshark_server_hellos": {"command": server_result, "rows": server_rows},
        "tshark_frames": {"command": frame_result, "rows": frame_rows},
        "tshark_dns_queries": {"command": dns_result, "rows": dns_rows},
        "foxio_ja4": {"command": ja4_result, "records": ja4_values},
        "foxio_ja4_main": {"command": main_result, "records": main_values},
        "foxio_ja4_with_keys": ({"command": keylog_result, "records": keylog_values}
                                 if keylog_result else None),
        "interpretation": "Tool output only; no limitation conclusion is inferred. FoxIO uses TShark for packet dissection.",
    }
    return row, raw


def write_markdown(rows: list[dict], path: Path) -> None:
    lines = ["# Reproduced Track 1 summary", "",
             "Generated by `code/scripts/analyze.py`; raw outputs are in `raw/`. "
             "A missing/empty result is not tool agreement.", "",
             "| " + " | ".join(TABLE_COLUMNS) + " |",
             "|" + "---|" * len(TABLE_COLUMNS)]
    for row in rows:
        cells = []
        for column in TABLE_COLUMNS:
            value = row.get(column)
            if isinstance(value, list):
                value = json.dumps(value, separators=(",", ":"))
            if value is None:
                value = "—"
            cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze(manifest: dict, *, output_dir: Path, capture_ids: set[str] | None = None,
            tshark: str = "tshark", ja4: str = "ja4", ja4_main: str = "ja4-main",
            timeout: int = 180) -> int:
    settings = manifest.get("lab_settings", {})
    entries = [entry for entry in manifest["captures"] if entry.get("capture_recipe")]
    if capture_ids is not None:
        entries = [entry for entry in entries if entry["capture_id"] in capture_ids]
        missing = capture_ids - {entry["capture_id"] for entry in entries}
        if missing:
            raise ValueError("not reproducible from the Track 1 lab manifest: " + ", ".join(sorted(missing)))
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    tool_versions = {
        "tshark": run((tshark, "--version"), timeout),
        "ja4": run((ja4, "--version"), timeout),
        "ja4_main": run((ja4_main, "--version"), timeout) if ja4_main else None,
    }
    rows = []
    for entry in entries:
        row, raw = _capture_analysis(entry, settings, tshark=tshark, ja4=ja4,
                                     ja4_main=ja4_main, timeout=timeout)
        rows.append(row)
        (raw_dir / f"{entry['capture_id']}.json").write_text(
            json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        print(f"analyzed {entry['capture_id']}: status={row['capture_status']} hellos={row['hellos_tshark']}")
    (output_dir / "summary.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    write_markdown(rows, output_dir / "summary.md")
    (output_dir / "run.json").write_text(json.dumps({
        "schema_version": 1,
        "manifest": "captures/manifest.json",
        "tools": tool_versions,
        "interpretation": "Recomputed outputs; not a limitation conclusion.",
    }, indent=2) + "\n", encoding="utf-8")
    return 0 if all(not row["tool_errors"] for row in rows) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results/reproduced"))
    parser.add_argument("--capture-id", action="append", dest="capture_ids")
    parser.add_argument("--tshark", default="tshark")
    parser.add_argument("--ja4", default="ja4")
    parser.add_argument("--ja4-main", default="ja4-main")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    try:
        return analyze(load_manifest(), output_dir=output_dir,
                       capture_ids=set(args.capture_ids) if args.capture_ids else None,
                       tshark=args.tshark, ja4=args.ja4,
                       ja4_main=args.ja4_main, timeout=args.timeout)
    except (OSError, ValueError) as exc:
        print(f"analysis error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
