#!/usr/bin/env python3
"""Validate the capture manifest and emit machine-generated corpus status.

This initial harness intentionally does not invent measurements. Capture records
are added only after the corresponding packet evidence has been committed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "corpus" / "manifest.json"


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
        capture_file = entry.get("capture_file")
        if not isinstance(capture_id, str) or not capture_id:
            raise ValueError(f"captures[{index}] needs a non-empty capture_id")
        if capture_id in seen:
            raise ValueError(f"duplicate capture_id: {capture_id}")
        seen.add(capture_id)
        if not isinstance(capture_file, str) or not capture_file:
            raise ValueError(f"{capture_id}: needs capture_file")
        path = (ROOT / capture_file).resolve()
        if ROOT.resolve() not in path.parents:
            raise ValueError(f"{capture_id}: capture_file must stay inside repository")
        if not path.is_file():
            raise ValueError(f"{capture_id}: capture does not exist: {capture_file}")
        if not isinstance(entry.get("commands", []), list):
            raise ValueError(f"{capture_id}: commands must be a list")
        if not isinstance(entry.get("expected_properties", []), list):
            raise ValueError(f"{capture_id}: expected_properties must be a list")
    return doc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        manifest = load_manifest()
    except ValueError as exc:
        print(f"manifest error: {exc}", file=sys.stderr)
        return 1
    summary = {
        "schema_version": 1,
        "capture_count": len(manifest["captures"]),
        "status": "validated" if manifest["captures"] else "no_evidence_yet",
        "note": "No capture records are present; no experimental result is claimed.",
    }
    if args.check_only:
        print(f"manifest valid: {summary['capture_count']} capture(s)")
        return 0
    output = args.output or ROOT / "results" / "evaluation.json"
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output.relative_to(ROOT) if ROOT in output.parents else output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
