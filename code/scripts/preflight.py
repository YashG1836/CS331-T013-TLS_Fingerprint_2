#!/usr/bin/env python3
"""Report whether the baseline-capture toolchain is ready.

This is a read-only environment probe. It does not capture traffic or claim
fingerprint results; it writes a machine-readable snapshot for the team VM.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
PROBES: dict[str, tuple[str, ...]] = {
    "cmake": ("cmake", "--version"),
    "compiler": ("g++", "--version"),
    "openssl": ("openssl", "version"),
    "tshark": ("tshark", "--version"),
    "tcpdump": ("tcpdump", "--version"),
    "dumpcap": ("dumpcap", "--version"),
    "curl": ("curl", "--version"),
    "caddy": ("caddy", "version"),
    "ethtool": ("ethtool", "--version"),
}
FINGERPRINT_FIELDS = (
    "tls.handshake.ja3",
    "tls.handshake.ja3s",
    "tls.handshake.ja4",
    "tls.handshake.ja4_r",
)


def run_probe(argv: Sequence[str], timeout: int = 12) -> dict:
    executable = shutil.which(argv[0])
    if executable is None:
        return {"available": False, "argv": list(argv), "error": f"{argv[0]} not found on PATH"}
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "argv": list(argv), "path": executable, "error": str(exc)}
    combined = (result.stdout + "\n" + result.stderr).strip()
    return {
        "available": True,
        "argv": list(argv),
        "path": executable,
        "exit_code": result.returncode,
        "version": combined.splitlines()[:4],
    }


def parse_tshark_fields(text: str) -> set[str]:
    fields: set[str] = set()
    for line in text.splitlines():
        parts = line.split("\t")
        # `tshark -G fields` emits `F<TAB>display name<TAB>abbreviation...`.
        if len(parts) >= 3 and parts[0] == "F":
            fields.add(parts[2])
    return fields


def inspect_tshark() -> dict:
    executable = shutil.which("tshark")
    if executable is None:
        return {"available": False, "error": "tshark not found on PATH"}
    try:
        raw = subprocess.run((executable, "-G", "fields"), capture_output=True, text=True, timeout=45, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "error": str(exc)}
    if raw.returncode != 0:
        return {"available": True, "exit_code": raw.returncode, "error": raw.stderr.strip() or "tshark -G fields failed"}
    # The complete field listing is intentionally not copied into the report.
    fields = parse_tshark_fields(raw.stdout)
    fingerprint_fields = {name: name in fields for name in FINGERPRINT_FIELDS}
    quic_fields = sorted(name for name in fields if name.startswith("quic."))
    return {
        "available": True,
        "exit_code": raw.returncode,
        "has_quic_fields": bool(quic_fields),
        "quic_field_count": len(quic_fields),
        "sample_quic_fields": quic_fields[:20],
        "fingerprint_fields": fingerprint_fields,
        "note": "Field availability is not proof that a capture is dissected or fingerprinted correctly.",
    }


def inspect_interfaces() -> dict:
    commands = (
        ("dumpcap", ("-D",)),
        ("tcpdump", ("-D",)),
        ("ip", ("-o", "link", "show")),
    )
    for executable, args in commands:
        path = shutil.which(executable)
        if path is None:
            continue
        try:
            result = subprocess.run((path, *args), capture_output=True, text=True, timeout=12, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            continue
        if result.returncode == 0:
            text = (result.stdout + "\n" + result.stderr).strip()
            return {"source": " ".join((executable, *args)), "available": True, "interfaces": text.splitlines()}
    return {"available": False, "error": "No interface-listing tool succeeded (dumpcap, tcpdump, or ip)."}


def build_report() -> dict:
    tools = {name: run_probe(argv) for name, argv in PROBES.items()}
    tshark = inspect_tshark()
    interfaces = inspect_interfaces()
    curl_text = "\n".join(tools["curl"].get("version", []))
    ready = all(tools[name].get("available") for name in ("cmake", "compiler", "openssl", "tshark"))
    ready = ready and any(tools[name].get("available") for name in ("tcpdump", "dumpcap"))
    return {
        "schema_version": 1,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": {"system": platform.system(), "release": platform.release(), "machine": platform.machine(), "python": sys.version.split()[0]},
        "tools": tools,
        "tshark_capabilities": tshark,
        "capture_interfaces": interfaces,
        "curl_http3_feature_advertised": "HTTP3" in curl_text.upper(),
        "baseline_capture_ready": ready,
        "interpretation": "Preflight only: no packet was captured and no fingerprint result was measured.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write JSON report here; otherwise print to stdout")
    parser.add_argument("--strict", action="store_true", help="return exit status 1 if baseline tools are missing")
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"wrote {output}")
    else:
        print(rendered, end="")
    return 1 if args.strict and not report["baseline_capture_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
