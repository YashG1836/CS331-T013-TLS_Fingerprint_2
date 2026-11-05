#!/usr/bin/env python3
"""Audit the repository's seven-row evidence without inventing live results.

This is an offline artifact audit, not a fresh capture campaign or ground-truth
oracle. Imported/user-run evidence is labeled as such. L6 remains NOT_MEASURED
until a packet-bearing IPv6 egress capture is supplied and reviewed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
BATCH_DIR = ROOT / "results" / "track2" / "verification-batch-20261104-201936"
RAW_DIR = ROOT / "results" / "raw"
PCAP_DIR = ROOT / "captures" / "pcaps"
RESULTS_DIR = ROOT / "results" / "reproduced" / "seven_rows_verification"
SUMMARY_PATH = RESULTS_DIR / "summary.json"

EXPECTED_CASES = {
    "baseline",
    "reverse-record-order",
    "shuffle-record-order",
    "drop-one-initial-crypto-record",
    "drop-every-third-initial-crypto-record",
    "truncate-middle-initial-crypto-record",
}
EXPECTED_TSHARK_JA4_PQ = "t13d3012h2_1d37bd780c83_7f037f8d6676"
EXPECTED_TSHARK_JA4_CLASSIC = "t13d3014h2_1d37bd780c83_3eb322dd144c"
GREASE_VALUES = {f"{x:02x}{x:02x}" for x in range(0x0A, 0x100, 0x10)}


class EvidenceError(RuntimeError):
    """Raised when a committed evidence artifact fails an explicit check."""


class ToolUnavailable(RuntimeError):
    """Raised when an optional live-verification dependency is not installed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def run_argv(argv: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    """Run one external tool with argv, never a shell command string."""
    if not argv or shutil.which(argv[0]) is None:
        raise ToolUnavailable(f"required executable is unavailable: {argv[0] if argv else '<empty>'}")
    try:
        result = subprocess.run(
            argv, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise EvidenceError(f"command timed out after {timeout}s: {argv[0]}") from exc
    except OSError as exc:
        raise ToolUnavailable(f"could not start {argv[0]}: {exc}") from exc
    if result.returncode != 0:
        raise EvidenceError(f"command exited {result.returncode}: {argv!r}; stderr={result.stderr.strip()}")
    return result


def tshark_fields(pcap: Path, display_filter: str, fields: list[str], *, no_tls_keys: bool = False, occurrence: str = "f") -> dict[str, Any]:
    """Extract tab-separated fields and record exact argv/version; fail closed."""
    executable = shutil.which("tshark")
    if executable is None:
        raise ToolUnavailable("tshark is unavailable")

    def invoke(extra_prefs: list[str]) -> subprocess.CompletedProcess[str]:
        argv = [executable, "-n", "-r", str(pcap), "-Y", display_filter,
                "-T", "fields", "-E", "separator=/t", "-E", f"occurrence={occurrence}"]
        for pref in extra_prefs:
            argv.extend(["-o", pref])
        for field in fields:
            argv.extend(["-e", field])
        return run_argv(argv)

    if no_tls_keys:
        with tempfile.TemporaryDirectory(prefix="seven-rows-keyless-") as tempdir:
            empty_keylog = Path(tempdir) / "empty.keys"
            empty_keylog.write_text("", encoding="ascii")
            result = invoke([f"tls.keylog_file:{empty_keylog}"])
    else:
        result = invoke([])
    version = run_argv([executable, "--version"]).stdout.splitlines()
    rows = [line.split("\t") for line in result.stdout.splitlines() if line.strip()]
    return {
        "argv": result.args,
        "returncode": result.returncode,
        "tshark_version": version[0] if version else "unknown",
        "rows": rows,
    }


def live_result(function: Any, *, enabled: bool, not_run_reason: str = "live verification disabled") -> dict[str, Any]:
    if not enabled:
        return {"status": "NOT_RUN", "reason": not_run_reason}
    try:
        return {"status": "PASS", **function()}
    except ToolUnavailable as exc:
        return {"status": "BLOCKED", "reason": str(exc)}
    except Exception as exc:
        return {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read valid JSON at {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"expected JSON object at {path.relative_to(ROOT)}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise EvidenceError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def read_track1_tool_versions() -> dict[str, str]:
    path = ROOT / "results" / "versions.txt"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise EvidenceError(f"cannot read imported Track 1 tool-version note: {exc}") from exc
    versions: dict[str, str] = {}
    for line in lines:
        if ": " in line:
            key, value = line.split(": ", 1)
            versions[key.strip()] = value.strip()
    return versions


def read_batch_metadata() -> dict[str, str]:
    path = BATCH_DIR / "environment.txt"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise EvidenceError(f"cannot read WSL batch environment metadata: {exc}") from exc
    metadata: dict[str, str] = {}
    for line in lines:
        if line.startswith(("timestamp=", "commit=", "branch=")):
            key, value = line.split("=", 1)
            metadata[key] = value
    require({"timestamp", "commit", "branch"} <= metadata.keys(), "WSL batch environment metadata incomplete")
    return metadata


def verify_batch_manifest() -> dict[str, Any]:
    """Verify the checked-in SHA256SUMS without shelling out to sha256sum."""
    manifest = BATCH_DIR / "SHA256SUMS"
    require(manifest.is_file(), "verification batch SHA256SUMS is missing")
    verified = 0
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            expected, relative = line.split(maxsplit=1)
        except ValueError as exc:
            raise EvidenceError(f"malformed SHA256SUMS line {number}") from exc
        relative = relative.lstrip("* ")
        target = (ROOT / relative).resolve()
        if ROOT.resolve() not in target.parents:
            raise EvidenceError(f"manifest path escapes repository at line {number}")
        require(target.is_file(), f"manifest file missing: {relative}")
        actual = sha256_file(target)
        require(actual == expected.lower(), f"SHA-256 mismatch: {relative}")
        verified += 1
    require(verified > 0, "empty verification-batch SHA256SUMS")
    return {
        "manifest": str(manifest.relative_to(ROOT)),
        "manifest_sha256": sha256_file(manifest),
        "files_verified": verified,
        "verification_method": "Python hashlib; paths constrained to repository",
    }


def run_l1_extractor() -> dict[str, Any]:
    """Build if possible, then execute the current C++ CLI on both QUIC PCAPs."""
    cpp_bin = ROOT / "build" / "code" / "quic" / "src" / "quic-fingerprint"
    if not cpp_bin.is_file():
        cmake = shutil.which("cmake")
        if cmake is None:
            raise ToolUnavailable("cmake and a prebuilt quic-fingerprint executable are both unavailable")
        build_dir = ROOT / "build"
        if not (build_dir / "CMakeCache.txt").is_file():
            run_argv([cmake, "-S", str(ROOT), "-B", str(build_dir), "-DCMAKE_BUILD_TYPE=Release"])
        run_argv([cmake, "--build", str(build_dir), "--target", "quic-fingerprint", "--parallel"] , timeout=600)
    require(cpp_bin.is_file(), "CMake completed without producing quic-fingerprint")

    inventory = read_json(BATCH_DIR / "quic-initial-dcid-inventory.json")
    expected_cids: dict[str, set[str]] = {}
    for capture in inventory["captures"]:
        name = Path(capture["input_pcap"]).stem
        expected_cids[name] = {
            dcid
            for flow in capture["flows"]
            for dcid in flow["later_client_dcids_matching_server_initial_scid_hex"]
        }
    results: dict[str, Any] = {}
    for client in ("curl", "chromium"):
        pcap = PCAP_DIR / f"quic_{client}.pcap"
        command = [str(cpp_bin), "--pcap", str(pcap)]
        output = run_argv(command, timeout=120)
        complete = len(re.findall(r"(?m)^client_hello=complete$", output.stdout))
        flow_rows = {
            dcid.lower(): int(failures)
            for dcid, failures in re.findall(r"(?m)^flow_dcid=([0-9a-f]+).*?decrypt_failures=(\d+)", output.stdout)
        }
        expected = expected_cids[f"quic_{client}"]
        require(complete == 5, f"{client}: live C++ extractor produced {complete} complete ClientHellos, expected five")
        require(len(expected) == 5, f"{client}: inventory does not identify five post-switch DCIDs")
        require(all(cid in flow_rows and flow_rows[cid] > 0 for cid in expected),
                f"{client}: live C++ output lacks a decrypt-failure bucket for every inventoried post-switch DCID")
        results[client] = {
            "command": command,
            "complete_client_hellos": complete,
            "post_switch_client_dcids_with_decrypt_failures": len(expected),
            "dcid_failure_counts": {cid: flow_rows[cid] for cid in sorted(expected)},
            "direction": "client-to-server; keyed to header inventory, not server-direction failures",
        }
    return {"status": "PASS", "executable": str(cpp_bin), "traces": results}


def verify_l1() -> dict[str, Any]:
    """Audit the batch and optionally rerun the current C++ extractor."""
    manifest_result = verify_batch_manifest()
    per_trace: dict[str, Any] = {}
    for client in ("chromium", "curl"):
        pcap = PCAP_DIR / f"quic_{client}.pcap"
        result_path = BATCH_DIR / "quic-impairment" / client / "impairment-results.json"
        data = read_json(result_path)
        require(data.get("source_sha256") == sha256_file(pcap), f"{client}: source PCAP hash mismatch")
        results = data.get("results")
        require(isinstance(results, list), f"{client}: results must be a list")
        by_case = {item.get("case_id"): item for item in results if isinstance(item, dict)}
        require(len(results) == len(by_case) == len(EXPECTED_CASES), f"{client}: duplicate or missing impairment case")
        require(set(by_case) == EXPECTED_CASES, f"{client}: unexpected impairment case set")

        for case_id, item in by_case.items():
            reference = item.get("reference_sha256")
            extracted = item.get("extracted_sha256")
            require(isinstance(reference, list) and isinstance(extracted, list), f"{client}/{case_id}: missing byte-hash multisets")
            require(Counter(reference) == Counter(extracted), f"{client}/{case_id}: reference/extractor byte hashes differ")
            require(item.get("multiset_equal") is True, f"{client}/{case_id}: batch did not record multiset equality")
            require(item.get("missed_reference_count") == 0, f"{client}/{case_id}: missed references")
            require(item.get("extra_or_nonreference_count") == 0, f"{client}/{case_id}: extra outputs")
            require(item.get("reference_count") == len(reference), f"{client}/{case_id}: reference count inconsistent with hashes")
            require(item.get("extracted_count") == len(extracted), f"{client}/{case_id}: extracted count inconsistent with hashes")
            require(item.get("exact_byte_match_count") == len(reference), f"{client}/{case_id}: exact match count inconsistent")
            require(math.isclose(float(item.get("exact_byte_recall", -1)), 1.0), f"{client}/{case_id}: recall is not 1.0")
            require(item.get("comparison_status") == "ok", f"{client}/{case_id}: comparison status is not ok")

        baseline = by_case["baseline"]
        require(baseline.get("reference_count") == 5, f"{client}: baseline reference count is not five")
        require(baseline.get("extracted_count") == 5, f"{client}: baseline extracted count is not five")
        require(by_case["drop-every-third-initial-crypto-record"].get("reference_count") == 2,
                f"{client}: every-third-drop comparator count is not two")
        per_trace[client] = {
            "baseline_reference_and_matches": 5,
            "cases": len(by_case),
            "matched_reference_outputs_across_cases": sum(len(item["reference_sha256"]) for item in by_case.values()),
            "misses": 0,
            "extras": 0,
            "comparison_scope": "TShark output from the same PCAP variant; user-run WSL batch",
            "tshark_version": data.get("tshark_version_line"),
        }

    inventory_path = BATCH_DIR / "quic-initial-dcid-inventory.json"
    inventory = read_json(inventory_path)
    captures = inventory.get("captures")
    require(isinstance(captures, list) and len(captures) == 2, "DCID inventory must contain both QUIC captures")
    post_switch: dict[str, int] = {}
    inventory_inputs: set[str] = set()
    for capture in captures:
        pcap_rel = capture.get("input_pcap")
        require(pcap_rel in {"captures/pcaps/quic_chromium.pcap", "captures/pcaps/quic_curl.pcap"},
                "DCID inventory references an unexpected input PCAP")
        inventory_inputs.add(pcap_rel)
        pcap = ROOT / pcap_rel
        require(capture.get("input_sha256") == sha256_file(pcap), f"DCID inventory source hash mismatch: {pcap_rel}")
        flows = capture.get("flows")
        require(isinstance(flows, list) and len(flows) == 5, f"{pcap_rel}: expected five inventoried UDP flows")
        matches = 0
        for flow in flows:
            client_ep = flow.get("client_endpoint", "")
            server_ep = flow.get("server_endpoint", "")
            require(client_ep.rsplit(":", 1)[-1] != "443" and server_ep.rsplit(":", 1)[-1] == "443",
                    f"{pcap_rel}: inventory flow is not labelled client-to-server by endpoint")
            later = set(flow.get("later_distinct_client_initial_dcids_hex", []))
            server_scids = {v for v in flow.get("server_initial_scids_hex", []) if v}
            matching = set(flow.get("later_client_dcids_matching_server_initial_scid_hex", []))
            require(matching and matching <= later and matching <= server_scids,
                    f"{pcap_rel}: switched client DCID is not cross-matched to server Initial SCID")
            matches += len(matching)
        require(matches == 5, f"{pcap_rel}: expected five post-switch client DCID matches")
        post_switch[Path(pcap_rel).stem] = matches
    require(inventory_inputs == {"captures/pcaps/quic_chromium.pcap", "captures/pcaps/quic_curl.pcap"},
            "DCID inventory does not contain exactly Chromium and curl")

    return {
        "status": "PASS",
        "evidence_class": "user-run WSL batch and committed header inventory; artifact audit only",
        "batch_run": read_batch_metadata(),
        "manifest": manifest_result,
        "per_trace": per_trace,
        "post_switch_client_dcid_matches": post_switch,
        "direction_interpretation": "client-to-server Initials; not server-direction decrypt attempts",
        "limits": [
            "No fresh TShark/C++ execution is performed by this offline audit.",
            "Byte comparison is against TShark on each same case-specific PCAP, not independent ground truth.",
            "Five switched-DCID buckets explain the inventory; they do not imply a missed ClientHello in these traces.",
        ],
    }


def live_l2_keyless() -> dict[str, Any]:
    pcap = PCAP_DIR / "tls_keylog_curl.pcap"
    extraction = tshark_fields(
        pcap, "tls.handshake.type == 1 || tls.handshake.certificate || http.request",
        ["tls.handshake.type", "tls.handshake.ja4", "tls.handshake.certificate", "http.request.method"],
        no_tls_keys=True,
    )
    rows = extraction["rows"]
    client_hellos = [row for row in rows if row and row[0] == "1"]
    require(client_hellos and all(len(row) > 1 and row[1] for row in client_hellos),
            "fresh keyless TShark pass did not expose ClientHello JA4")
    require(not any(len(row) > 2 and row[2] for row in rows),
            "fresh keyless TShark pass unexpectedly exposed certificate details")
    require(not any(len(row) > 3 and row[3] for row in rows),
            "fresh keyless TShark pass unexpectedly exposed HTTP requests")
    return {"tshark": extraction["tshark_version"], "command": extraction["argv"],
            "client_hellos_with_ja4": len(client_hellos), "certificate_rows": 0, "http_rows": 0,
            "scope": "fresh re-dissection with an explicitly empty TLS key log; not fresh network traffic"}


def live_pcap_parse_checks() -> dict[str, dict[str, Any]]:
    """Fresh TShark field extraction for rows whose underlying captures are imported."""
    results: dict[str, dict[str, Any]] = {}
    # L3: independently re-read both supplied captures and count SYN observations.
    def l3() -> dict[str, Any]:
        profiles = {}
        for label in ("offload_on", "offload_off"):
            extracted = tshark_fields(
                PCAP_DIR / f"tls_{label}.pcap", "tcp.flags.syn == 1",
                ["tcp.flags.ack", "tcp.options.mss_val", "tcp.options.wscale.shift", "tcp.window_size_value", "ip.ttl", "frame.len"],
            )
            rows = extracted["rows"]
            require(len(rows) == 6, f"{label}: live TShark found {len(rows)} SYN rows, expected six")
            profiles[label] = {"tshark": extracted["tshark_version"], "syn_rows": rows, "command": extracted["argv"]}
        require(profiles["offload_on"]["syn_rows"] == profiles["offload_off"]["syn_rows"],
                "live TShark SYN fields differ between supplied offload captures")
        return {"profiles": profiles, "same_profile": True,
                "scope": "fresh parse of imported captures; does not toggle offload or establish a proxy boundary"}
    results["L3_VANTAGE_OFFLOAD"] = live_result(l3, enabled=True)

    def arm_live(filename: str, label: str, expected_length: str, expected_group: str, expected_ja4: str) -> dict[str, Any]:
        pcap = PCAP_DIR / filename
        extracted = tshark_fields(
            pcap, "tls.handshake.type == 1 || tls.handshake.type == 2",
            ["tls.handshake.type", "tls.handshake.length", "tls.handshake.ja4", "tls.handshake.extensions_key_share_group"],
        )
        hellos = [row for row in extracted["rows"] if row and row[0] == "1"]
        servers = [row for row in extracted["rows"] if row and row[0] == "2"]
        require(len(hellos) == 5, f"{label}: fresh TShark found {len(hellos)} ClientHellos, expected five")
        require(len(servers) == 5, f"{label}: fresh TShark found {len(servers)} ServerHellos, expected five")
        require({row[1] for row in hellos if len(row) > 1} == {expected_length}, f"{label}: live handshake length differs")
        require({row[3] for row in servers if len(row) > 3} == {expected_group}, f"{label}: live selected group differs")
        require({row[2] for row in hellos if len(row) > 2} == {expected_ja4}, f"{label}: live JA4 differs")
        return {"tshark": extracted["tshark_version"], "client_hellos": hellos, "server_hellos": servers,
                "command": extracted["argv"]}
    def l4() -> dict[str, Any]:
        pq = arm_live("tls_pq_on.pcap", "pq", "1511", "4588", EXPECTED_TSHARK_JA4_PQ)
        classic = arm_live("tls_pq_off.pcap", "classic", "508", "29", EXPECTED_TSHARK_JA4_CLASSIC)
        return {"pq": pq, "classic": classic, "ja4_diverges": True,
                "scope": "fresh dissection of imported PQ/classic captures; field length is not on-wire segment size"}
    results["L4_PQ_MLKEM"] = live_result(l4, enabled=True)

    def l5() -> dict[str, Any]:
        extracted = tshark_fields(
            PCAP_DIR / "tls_chromium_repeat.pcap", "tls.handshake.type == 1",
            ["tls.handshake.ja3", "tls.handshake.ja4", "tls.handshake.sig_hash_alg"],
        )
        rows = extracted["rows"]
        require(len(rows) == 50, f"L5: fresh TShark found {len(rows)} ClientHellos, expected 50")
        ja3 = [row[0] for row in rows if row and row[0]]
        ja4 = [row[1] for row in rows if len(row) > 1 and row[1]]
        require(len(ja3) == 50 and len(set(ja3)) == 50, "L5: fresh JA3 count is not 50 distinct values")
        require(len(ja4) == 50 and len(set(ja4)) == 15, "L5: fresh JA4 count is not 15 distinct values")
        def to_grease(value: str) -> str:
            number = int(value, 0) if value.lower().startswith("0x") else int(value, 10)
            return f"{(number >> 8) & 0xff:02x}{number & 0xff:02x}"
        grease_values = [to_grease(row[2]) for row in rows if len(row) > 2 and row[2]]
        require(len(grease_values) == 50 and all(_is_grease(value) for value in grease_values),
                "L5: fresh first signature-algorithm values are not GREASE")
        require(len(set(grease_values)) == 15, "L5: fresh signature GREASE count is not 15")
        require(len({(ja4_value, grease) for ja4_value, grease in zip(ja4, grease_values)}) == 15,
                "L5: fresh JA4-to-GREASE relationship is not one-to-one in this sample")
        return {"tshark": extracted["tshark_version"], "observations": len(rows), "distinct_ja3": len(set(ja3)),
                "distinct_ja4": len(set(ja4)), "distinct_first_signature_grease_values": sorted(set(grease_values)),
                "rows": rows, "command": extracted["argv"],
                "scope": "fresh re-dissection of the imported 50-hello capture; not 50 new connections"}
    results["L5_GREASE_STABILITY"] = live_result(l5, enabled=True)

    def l7() -> dict[str, Any]:
        arms = {}
        for mode in ("off", "on"):
            extracted = tshark_fields(
                PCAP_DIR / f"tls_ech_{mode}.pcap", "tls.handshake.type == 1",
                ["tls.handshake.extensions_server_name", "tls.handshake.ja4", "tls.handshake.extension.type"],
                occurrence="a",
            )
            rows = extracted["rows"]
            require(len(rows) == 5, f"L7 {mode}: fresh TShark found {len(rows)} ClientHellos, expected five")
            names = [row[0] for row in rows]
            types = [row[2].lower() for row in rows if len(row) > 2]
            ech_rows = sum("fe0d" in value or "65037" in value for value in types)
            arms[mode] = {"tshark": extracted["tshark_version"], "rows": rows,
                          "target_name_count": names.count("crypto.cloudflare.com"),
                          "public_name_count": names.count("cloudflare-ech.com"),
                          "ech_extension_rows": ech_rows, "command": extracted["argv"]}
        require(arms["off"]["target_name_count"] == 2 and arms["off"]["ech_extension_rows"] == 0,
                "L7 fresh ECH-off data differs")
        require(arms["on"]["target_name_count"] == 0 and arms["on"]["public_name_count"] == 2
                and arms["on"]["ech_extension_rows"] == 5, "L7 fresh ECH-on data differs")
        return {"arms": arms, "scope": "fresh dissection of imported captures; target flow/page correlation is not proved"}
    results["L7_ECH"] = live_result(l7, enabled=True)
    return results


def verify_l2() -> dict[str, Any]:
    """Audit the imported no-key/key-enabled outputs; do not claim a new wire test."""
    data = read_json(RAW_DIR / "tls_keylog_curl.json")
    plain_rows = data.get("foxio_ja4")
    keyed_rows = data.get("foxio_ja4_with_keys")
    require(isinstance(plain_rows, list) and len(plain_rows) == 1, "L2 imported no-key result is not one stream")
    require(isinstance(keyed_rows, list) and len(keyed_rows) == 1, "L2 imported key-enabled result is not one stream")
    plain, keyed = plain_rows[0], keyed_rows[0]
    hellos = data.get("tshark_client_hellos")
    server_hellos = data.get("tshark_server_hellos")
    require(isinstance(hellos, list) and len(hellos) == 1, "L2 expected one saved ClientHello")
    require(isinstance(server_hellos, list) and len(server_hellos) == 1, "L2 expected one saved ServerHello")
    require(str(hellos[0].get("tls.handshake.ja4", "")).startswith("t13"), "L2 TShark ClientHello output does not identify TLS 1.3")
    require(server_hellos[0].get("tls.handshake.extensions_key_share_group") == "4588", "L2 expected the saved TLS 1.3 key-share group")
    require(str(plain.get("ja4", "")).startswith("t13"), "L2 no-key output does not identify TLS 1.3")
    require(str(plain.get("ja4s", "")).startswith("t13"), "L2 server output does not identify TLS 1.3")
    require("tls_certs" not in plain and "http" not in plain, "L2 no-key output unexpectedly contains cert/HTTP details")
    certs = keyed.get("tls_certs")
    http = keyed.get("http")
    require(isinstance(certs, list) and certs, "L2 key-enabled output has no certificate evidence")
    require(isinstance(http, list) and http, "L2 key-enabled output has no HTTP evidence")
    x509 = [cert for cert_set in certs for cert in cert_set.get("x509", [])]
    require(x509 and all(cert.get("ja4x") for cert in x509), "L2 key-enabled output is missing JA4X certificate records")
    require(all(row.get("ja4h") for row in http), "L2 key-enabled output is missing JA4H HTTP records")
    return {
        "status": "PASS",
        "evidence_class": "imported Track 1 JSON comparison",
        "reported_tool_versions": read_track1_tool_versions(),
        "tls13_indicator": "JA4/JA4S version prefix t13 in imported output",
        "without_keys": {"ja4_present": True, "certificate_details": 0, "http_details": 0},
        "with_keys": {"certificate_records": len(x509), "http_records": len(http)},
        "limits": [
            "The TLS key log is intentionally not present; this verifier audits saved outputs, not a fresh re-dissection.",
            "The protocol encryption claim is scoped to this TLS 1.3 sample and the recorded keyless/keyed tool outputs.",
        ],
    }


def verify_l3() -> dict[str, Any]:
    """Audit both offload captures while explicitly refusing proxy attribution."""
    data = read_json(BATCH_DIR / "offload-syn-analysis.json")
    captures = data.get("captures")
    require(isinstance(captures, list), "L3 capture list is missing")
    by_label = {row.get("label"): row for row in captures if isinstance(row, dict)}
    require(set(by_label) == {"offload_on", "offload_off"}, "L3 requires separate on/off captures")
    profiles: dict[str, Any] = {}
    for label, row in by_label.items():
        capture_pcap = row.get("pcap", "")
        capture_id = Path(capture_pcap).stem
        pcap = PCAP_DIR / f"{capture_id}.pcap"
        require(pcap.is_file() and row.get("sha256") == sha256_file(pcap), f"L3 {label}: source PCAP hash mismatch")
        streams = row.get("streams")
        require(row.get("syn_observation_count") == 6, f"L3 {label}: expected six SYN observations")
        require(isinstance(streams, dict) and len(streams) == 3, f"L3 {label}: expected three SYN/SYN-ACK streams")
        profile_rows = []
        for stream in streams.values():
            require(stream.get("observation_status") == "complete_syn_pair", f"L3 {label}: incomplete SYN pair")
            syn = stream.get("client_syn", {})
            synack = stream.get("peer_synack", {})
            require(syn.get("role") == "syn" and synack.get("role") == "synack", f"L3 {label}: role labels are invalid")
            require(syn.get("src") == synack.get("dst") and syn.get("dst") == synack.get("src"),
                    f"L3 {label}: SYN/SYN-ACK endpoints do not reverse")
            asymmetry = set(stream.get("same_capture_option_asymmetry", []))
            require(asymmetry == {"mss", "window_scale", "window"}, f"L3 {label}: unexpected option-asymmetry fields")
            profile_rows.append({
                "client": [syn.get("mss"), syn.get("window_scale"), syn.get("window"), syn.get("ttl")],
                "peer": [synack.get("mss"), synack.get("window_scale"), synack.get("window"), synack.get("ttl")],
                "frame_lengths": [syn.get("frame_length"), synack.get("frame_length")],
                "asymmetry": sorted(asymmetry),
            })
        expected = {"client": [1460, 10, 64240, 64], "peer": [65495, 7, 65408, 63], "frame_lengths": [74, 74]}
        require(all({k: v[k] for k in expected} == expected for v in profile_rows),
                f"L3 {label}: expected repeated SYN profiles not present")
        profiles[label] = {
            "streams": len(profile_rows),
            "unique_profiles": profile_rows,
            "tshark_version": row.get("tshark_version"),
        }

    on_set = {(tuple(r["client"]), tuple(r["peer"])) for r in profiles["offload_on"]["unique_profiles"]}
    off_set = {(tuple(r["client"]), tuple(r["peer"])) for r in profiles["offload_off"]["unique_profiles"]}
    require(on_set == off_set, "L3 profiles differ across the two supplied captures")
    return {
        "status": "PASS",
        "evidence_class": "user-run WSL TShark analysis of two imported single-vantage PCAPs",
        "profiles": profiles,
        "offload_toggle_changed_syn_profile": False,
        "proxy_or_tcp_termination": "NOT_ESTABLISHED",
        "limits": [
            "The two PCAPs are not synchronized captures across a known boundary.",
            "MSS 65495 is an advertised receive MSS; this evidence does not identify the peer or prove proxying.",
            "The identical SYN profiles do not demonstrate a TSO/GSO-induced MSS change; segment-size effects are a separate question.",
        ],
    }


def verify_l4() -> dict[str, Any]:
    """Audit every saved PQ/classic observation and preserve the length-field caveat."""
    pq = read_json(RAW_DIR / "tls_pq_on.json")
    classic = read_json(RAW_DIR / "tls_pq_off.json")
    expected = [
        ("pq", pq, 1511, "4588", EXPECTED_TSHARK_JA4_PQ, 12),
        ("classic", classic, 508, "29", EXPECTED_TSHARK_JA4_CLASSIC, 14),
    ]
    verified: dict[str, Any] = {}
    for label, data, expected_length, expected_group, expected_ja4, expected_ext_count in expected:
        hellos = data.get("tshark_client_hellos")
        server_hellos = data.get("tshark_server_hellos")
        foxio = data.get("foxio_ja4")
        require(isinstance(hellos, list) and len(hellos) == 5, f"L4 {label}: expected five ClientHellos")
        require(isinstance(server_hellos, list) and len(server_hellos) == 5, f"L4 {label}: expected five ServerHellos")
        require(isinstance(foxio, list) and len(foxio) == 5, f"L4 {label}: expected five JA4 output rows")
        require({int(row["tls.handshake.length"]) for row in hellos} == {expected_length}, f"L4 {label}: ClientHello field length differs")
        require({row["tls.handshake.extensions_key_share_group"] for row in server_hellos} == {expected_group},
                f"L4 {label}: selected server key-share group differs")
        ja4s = {row["tls.handshake.ja4"] for row in hellos}
        foxio_ja4s = {row["ja4"] for row in foxio}
        require(ja4s == {expected_ja4} and foxio_ja4s == {expected_ja4}, f"L4 {label}: JA4 differs from saved expected value")
        prefix = expected_ja4.split("_", 1)[0]
        require(int(prefix[6:8]) == expected_ext_count, f"L4 {label}: JA4 extension count differs")
        verified[label] = {
            "client_hellos": len(hellos),
            "tshark_tls_handshake_length_field": expected_length,
            "selected_server_group_decimal": expected_group,
            "ja4": expected_ja4,
            "ja4_extension_count": expected_ext_count,
        }
    return {
        "status": "PASS",
        "evidence_class": "imported Track 1 raw JSON audit",
        "reported_tool_versions": read_track1_tool_versions(),
        "arms": verified,
        "ja4_diverges": verified["pq"]["ja4"] != verified["classic"]["ja4"],
        "limits": [
            "1511 and 508 are TShark tls.handshake.length field values, not a direct on-wire segment measurement.",
            "The JA4 change is observed alongside extension count/content differences; it is not evidence JA4 directly encodes the selected group.",
            "This audit does not verify TCP segmentation or reassembly, and is one imported client/environment.",
        ],
    }


def _is_grease(value: str) -> bool:
    return value.lower() in GREASE_VALUES


def verify_l5() -> dict[str, Any]:
    """Audit saved JA3/JA4 output and correlate JA4 changes with GREASE fields."""
    data = read_json(RAW_DIR / "tls_chromium_repeat.json")
    hellos = data.get("tshark_client_hellos")
    foxio = data.get("foxio_ja4")
    require(isinstance(hellos, list) and len(hellos) == 50, "L5 expected 50 ClientHello observations")
    require(isinstance(foxio, list) and len(foxio) == 50, "L5 expected 50 raw JA4 rows")
    ja3s = [row.get("tls.handshake.ja3") for row in hellos]
    tshark_ja4s = [row.get("tls.handshake.ja4") for row in hellos]
    foxio_ja4s = [row.get("ja4") for row in foxio]
    require(None not in ja3s and len(set(ja3s)) == 50, "L5 JA3 observations are not 50 distinct values")
    require(Counter(tshark_ja4s) == Counter(foxio_ja4s), "L5 TShark/FoxIO JA4 values differ in the imported JSON")
    require(len(set(tshark_ja4s)) == 15, "L5 expected 15 saved JA4 values")

    raw_parts = [str(row.get("ja4_r", "")).split("_") for row in foxio]
    require(all(len(parts) == 4 for parts in raw_parts), "L5 raw JA4 fields do not have the expected four components")
    require(len({tuple(parts[:3]) for parts in raw_parts}) == 1, "L5 non-signature JA4 raw components also vary")
    sig_lists = [parts[3].split(",") for parts in raw_parts]
    first_signature_values = {values[0].lower() for values in sig_lists if values}
    require(len(first_signature_values) == 15, "L5 expected 15 distinct first signature-algorithm values")
    require(all(_is_grease(value) for value in first_signature_values), "L5 first signature values are not all RFC 8701 GREASE codes")
    require(len({tuple(values[1:]) for values in sig_lists}) == 1, "L5 non-first signature-algorithm values also vary")
    require(len({(ja4, values[0].lower()) for ja4, values in zip(foxio_ja4s, sig_lists)}) == 15,
            "L5 JA4-to-GREASE mapping is not one-to-one in this imported sample")

    sni_counts = Counter(row.get("tls.handshake.extensions_server_name", "") for row in hellos)
    return {
        "status": "PASS",
        "evidence_class": "imported Track 1 JSON audit",
        "reported_tool_versions": read_track1_tool_versions(),
        "client_hello_observations": 50,
        "distinct_ja3": len(set(ja3s)),
        "distinct_saved_ja4": len(set(tshark_ja4s)),
        "distinct_first_signature_grease_values": sorted(first_signature_values),
        "other_signature_algorithm_values_constant": True,
        "non_signature_ja4_components_constant": True,
        "observed_sni_counts": dict(sorted(sni_counts.items())),
        "limits": [
            "These are 50 ClientHello observations in one imported capture, not 50 newly generated controlled runs.",
            "The raw fields strongly correlate GREASE variation with JA4 variation in this sample; no current-version binary or ja4-main output is rerun here.",
            "The reported ja4-main distinct count of one has no retained per-capture raw output for verification.",
        ],
    }


def preserve_ipv6_loopback_capture(capture: Path, output_dir: Path, run_id: str | None = None) -> Path:
    """Copy a reviewed local-loopback PCAP without retaining its temporary key/certificate."""
    require(capture.is_file() and capture.stat().st_size > 24,
            "cannot preserve an absent or empty IPv6 loopback capture")
    output_dir.mkdir(parents=True, exist_ok=True)
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = output_dir / f"ipv6-loopback-{run_id}.pcap"
    require(not destination.exists(), f"refusing to overwrite existing IPv6 capture: {destination}")
    shutil.copy2(capture, destination)
    return destination


def live_ipv6_loopback(output_dir: Path | None = None) -> dict[str, Any]:
    """Capture one real local TLS handshake on ::1; never call this public egress."""
    tcpdump = shutil.which("tcpdump")
    openssl = shutil.which("openssl")
    if tcpdump is None:
        raise ToolUnavailable("tcpdump is unavailable; cannot capture the controlled loopback TLS exchange")
    if openssl is None:
        raise ToolUnavailable("openssl is unavailable; cannot create a temporary loopback TLS certificate")
    if shutil.which("tshark") is None:
        raise ToolUnavailable("tshark is unavailable; cannot extract the controlled loopback JA4")

    with tempfile.TemporaryDirectory(prefix="seven-rows-ipv6-") as tempdir:
        temp = Path(tempdir)
        cert, key, pcap = temp / "cert.pem", temp / "key.pem", temp / "ipv6-loopback.pcap"
        run_argv([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=localhost",
                  "-keyout", str(key), "-out", str(cert), "-days", "1"], timeout=60)

        listener = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("::1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
        except OSError as exc:
            listener.close()
            raise ToolUnavailable(f"IPv6 loopback listener unavailable: {exc}") from exc
        server_errors: list[str] = []
        def serve() -> None:
            try:
                raw, _ = listener.accept()
                with raw:
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    context.load_cert_chain(str(cert), str(key))
                    with context.wrap_socket(raw, server_side=True) as stream:
                        stream.recv(4096)
                        stream.sendall(b"HTTP/1.0 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
            except Exception as exc:
                server_errors.append(f"{type(exc).__name__}: {exc}")
            finally:
                listener.close()
        server = threading.Thread(target=serve, daemon=True)
        server.start()
        tcpdump_command = [tcpdump, "-i", "lo", "-U", "-w", str(pcap), "ip6 and tcp port", str(port)]
        capture = subprocess.Popen(
            tcpdump_command,
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            time.sleep(0.5)
            if capture.poll() is not None:
                _, stderr = capture.communicate()
                raise ToolUnavailable(f"tcpdump could not capture on loopback: {stderr.strip()}")
            client_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            client_context.check_hostname = False
            client_context.verify_mode = ssl.CERT_NONE
            with socket.create_connection(("::1", port), timeout=5) as raw:
                with client_context.wrap_socket(raw, server_hostname="localhost") as stream:
                    stream.sendall(b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n")
                    response = stream.recv(4096)
            require(response.startswith(b"HTTP/1.0 200"), "loopback TLS server did not return the controlled response")
        except OSError as exc:
            raise ToolUnavailable(f"could not perform controlled TLS exchange over ::1: {exc}") from exc
        finally:
            try:
                if capture.poll() is None:
                    capture.send_signal(signal.SIGINT)
                _, stderr = capture.communicate(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                capture.kill()
                _, stderr = capture.communicate()
            server.join(timeout=5)
        require(not server.is_alive(), "loopback TLS server thread did not stop")
        require(not server_errors, f"loopback TLS server error: {server_errors}")
        require(pcap.is_file() and pcap.stat().st_size > 24, "tcpdump produced no packet-bearing IPv6 PCAP")
        output_dir = output_dir or (RESULTS_DIR / "ipv6-loopback")
        preserved_pcap = preserve_ipv6_loopback_capture(pcap, output_dir)
        capture_hash = hashlib.sha256(preserved_pcap.read_bytes()).hexdigest()
        capture_ref = str(preserved_pcap.relative_to(ROOT)) if preserved_pcap.is_relative_to(ROOT) else str(preserved_pcap)
        capture_metadata = {
            "tcpdump_command": tcpdump_command,
            "tcpdump_returncode": capture.returncode,
            "tcpdump_stderr": stderr.strip(),
        }
        sidecar = preserved_pcap.with_suffix(".json")
        try:
            extraction = tshark_fields(
                preserved_pcap, "ipv6 && tls.handshake.type == 1",
                ["ipv6.src", "ipv6.dst", "tls.handshake.type", "tls.handshake.ja4"],
            )
            require(extraction["rows"] and all(row[3] for row in extraction["rows"] if len(row) > 3),
                    f"controlled IPv6 loopback ClientHello JA4 not extracted; raw capture retained at {preserved_pcap}")
        except Exception as exc:
            failure_evidence = {
                "scope": "controlled local ::1 TLS only; not public IPv6 egress",
                "public_ipv6_egress": "NOT_TESTED",
                "pcap_path": capture_ref,
                "pcap_sha256": capture_hash,
                "pcap_bytes": preserved_pcap.stat().st_size,
                **capture_metadata,
                "post_capture_validation_error": f"{type(exc).__name__}: {exc}",
            }
            sidecar.write_text(json.dumps(failure_evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            raise
        evidence = {
            "scope": "controlled local ::1 TLS only; not public IPv6 egress",
            "public_ipv6_egress": "NOT_TESTED",
            "interface": "lo",
            "server_address": "::1",
            "server_port": port,
            "pcap_path": capture_ref,
            "pcap_sha256": capture_hash,
            "pcap_bytes": preserved_pcap.stat().st_size,
            **capture_metadata,
            "client_hello_rows": extraction["rows"],
            "tshark_version": extraction["tshark_version"],
            "tshark_command": extraction["argv"],
            "server_response_received": True,
        }
        sidecar.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        evidence["evidence_json_path"] = str(sidecar.relative_to(ROOT)) if sidecar.is_relative_to(ROOT) else str(sidecar)
        return evidence


def verify_l6() -> dict[str, Any]:
    """Report the empty IPv6 attempt honestly; do not substitute loopback for egress."""
    path = PCAP_DIR / "tls_ipv6.pcap"
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise EvidenceError(f"cannot read L6 capture: {exc}") from exc
    require(len(payload) >= 24, "L6 capture is shorter than a classic-PCAP global header")
    known_magic = {b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d"}
    require(payload[:4] in known_magic, "L6 file does not have a recognized classic-PCAP magic value")
    packet_records = 0
    cursor = 24
    while cursor < len(payload):
        require(cursor + 16 <= len(payload), "L6 PCAP has a truncated packet-record header")
        captured_length = int.from_bytes(payload[cursor + 8:cursor + 12], "little" if payload[:4] in {b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"} else "big")
        cursor += 16
        require(cursor + captured_length <= len(payload), "L6 PCAP has a truncated packet record")
        cursor += captured_length
        packet_records += 1
    require(cursor == len(payload), "L6 PCAP record parsing did not end at EOF")
    require(packet_records == 0, f"L6 committed capture unexpectedly has {packet_records} packet records; review it manually")
    return {
        "status": "NOT_MEASURED",
        "evidence_class": "empty imported capture audit",
        "committed_capture_bytes": len(payload),
        "committed_packet_records": packet_records,
        "public_ipv6_egress": "NOT_TESTED",
        "loopback_is_not_substituted": True,
        "next_evidence_needed": "A packet-bearing capture of a controlled connection over the host's actual public IPv6 egress, with interface, route, command, timestamps, and hashes.",
    }


def verify_l7() -> dict[str, Any]:
    """Audit target SNI observations and ECH extension; report background names."""
    off = read_json(RAW_DIR / "tls_ech_off.json")
    on = read_json(RAW_DIR / "tls_ech_on.json")
    off_hellos = off.get("tshark_client_hellos")
    on_hellos = on.get("tshark_client_hellos")
    off_raw = off.get("foxio_ja4")
    on_raw = on.get("foxio_ja4")
    require(isinstance(off_hellos, list) and len(off_hellos) == 5, "L7 ECH-off capture should have five ClientHello rows")
    require(isinstance(on_hellos, list) and len(on_hellos) == 5, "L7 ECH-on capture should have five ClientHello rows")
    require(isinstance(off_raw, list) and len(off_raw) == 5, "L7 ECH-off raw JA4 rows missing")
    require(isinstance(on_raw, list) and len(on_raw) == 5, "L7 ECH-on raw JA4 rows missing")
    off_sni = [row.get("tls.handshake.extensions_server_name", "") for row in off_hellos]
    on_sni = [row.get("tls.handshake.extensions_server_name", "") for row in on_hellos]
    require(off_sni.count("crypto.cloudflare.com") == 2, "L7 expected two target-name ECH-off rows")
    require(on_sni.count("crypto.cloudflare.com") == 0, "L7 target name appears in saved ECH-on outer SNI rows")
    require(on_sni.count("cloudflare-ech.com") == 2, "L7 expected two public-name ECH-on rows")

    def has_ech_extension(row: dict[str, Any]) -> bool:
        parts = str(row.get("ja4_r", "")).split("_")
        return len(parts) == 4 and "fe0d" in {item.lower() for item in parts[2].split(",")}

    require(not any(has_ech_extension(row) for row in off_raw), "L7 ECH extension unexpectedly present in ECH-off raw outputs")
    require(all(has_ech_extension(row) for row in on_raw), "L7 ECH extension missing from one or more ECH-on ClientHellos")
    off_set, on_set = set(off_sni), set(on_sni)
    background = sorted(on_set - {"cloudflare-ech.com", "crypto.cloudflare.com"})
    return {
        "status": "PASS",
        "evidence_class": "imported Track 1 packet JSON plus team-supplied page observations",
        "reported_tool_versions": read_track1_tool_versions(),
        "ech_off": {"client_hello_rows": len(off_sni), "target_outer_sni_rows": off_sni.count("crypto.cloudflare.com"), "sn_names": sorted(off_set)},
        "ech_on": {"client_hello_rows": len(on_sni), "target_outer_sni_rows": on_sni.count("crypto.cloudflare.com"), "public_name_rows": on_sni.count("cloudflare-ech.com"), "ech_extension_rows": sum(has_ech_extension(row) for row in on_raw), "sn_names": sorted(on_set)},
        "other_visible_background_sni": background,
        "target_flow_correlation": "not present in the saved per-row export; page output is team-supplied",
        "limits": [
            "The capture-wide outer SNI set is not only cloudflare-ech.com; unrelated Chromium background names remain visible.",
            "The sample supports the target-name/public-name observation, but does not prove ECH+DoH success or broad name privacy.",
        ],
    }


def overall_status(rows: dict[str, dict[str, Any]]) -> str:
    statuses = {row.get("status") for row in rows.values()}
    if "FAIL" in statuses:
        return "FAIL"
    if statuses <= {"PASS"}:
        return "PASS"
    return "INCOMPLETE"


def run_all(
    *, live: bool = False, ipv6_loopback: bool = False,
    ipv6_loopback_output_dir: Path | None = None,
) -> dict[str, Any]:
    verifiers = {
        "L1_QUIC": verify_l1,
        "L2_TLS_SECRETS": verify_l2,
        "L3_VANTAGE_OFFLOAD": verify_l3,
        "L4_PQ_MLKEM": verify_l4,
        "L5_GREASE_STABILITY": verify_l5,
        "L6_IPV6": verify_l6,
        "L7_ECH": verify_l7,
    }
    rows: dict[str, dict[str, Any]] = {}
    for label, verifier in verifiers.items():
        try:
            rows[label] = verifier()
        except Exception as exc:
            rows[label] = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
    status = overall_status(rows)
    live_checks = {
        "L1_QUIC": live_result(run_l1_extractor, enabled=live),
        "L2_TLS_SECRETS": live_result(live_l2_keyless, enabled=live),
        "L3_VANTAGE_OFFLOAD": {"status": "NOT_RUN", "reason": "live mode disabled"},
        "L4_PQ_MLKEM": {"status": "NOT_RUN", "reason": "live mode disabled"},
        "L5_GREASE_STABILITY": {"status": "NOT_RUN", "reason": "live mode disabled"},
        "L6_IPV6": live_result(
            lambda: live_ipv6_loopback(ipv6_loopback_output_dir),
            enabled=ipv6_loopback,
            not_run_reason="use --ipv6-loopback to attempt a real ::1 capture; public IPv6 egress is not tested",
        ),
        "L7_ECH": {"status": "NOT_RUN", "reason": "live mode disabled"},
    }
    if live:
        live_checks.update(live_pcap_parse_checks())
    live_statuses = {value.get("status") for value in live_checks.values()}
    if "FAIL" in live_statuses:
        live_status = "FAIL"
    elif live_statuses == {"PASS"}:
        live_status = "PASS"
    else:
        live_status = "INCOMPLETE"
    return {
        "schema_version": 3,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "verification_mode": "offline evidence audit plus optional fresh tool re-dissection and controlled local IPv6 loopback capture",
        "overall_status": status,
        "overall_live_status": live_status,
        "live_options": {
            "live_tool_checks_requested": live,
            "ipv6_loopback_requested": ipv6_loopback,
            "ipv6_loopback_output_dir": str(ipv6_loopback_output_dir or (RESULTS_DIR / "ipv6-loopback")) if ipv6_loopback else None,
        },
        "exit_code": 0 if status == "PASS" else (1 if status == "FAIL" else 2),
        "rows": rows,
        "live_checks": live_checks,
        "course_rubric_note": "The repository contains project plans/proposal requirements but no standalone grading rubric; this output cannot certify rubric compliance or novelty.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="attempt C++ and TShark checks on the committed captures")
    parser.add_argument("--ipv6-loopback", action="store_true", help="attempt a fresh local ::1 TLS capture; this does not test public IPv6 egress")
    parser.add_argument("--ipv6-loopback-output-dir", type=Path, default=RESULTS_DIR / "ipv6-loopback",
                        help="directory for the packet-bearing loopback PCAP and metadata JSON")
    parser.add_argument("--output", type=Path, default=SUMMARY_PATH,
                        help="write the seven-row summary JSON here (default: results/reproduced/...)")
    args = parser.parse_args()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = run_all(
        live=args.live,
        ipv6_loopback=args.ipv6_loopback,
        ipv6_loopback_output_dir=args.ipv6_loopback_output_dir.expanduser().resolve(),
    )
    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    temporary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, output_path)
    passed = sum(row.get("status") == "PASS" for row in summary["rows"].values())
    print(f"Seven-row artifact audit: {passed}/7 PASS; overall={summary['overall_status']}; live={summary['overall_live_status']}")
    for name, row in summary["rows"].items():
        live_status = summary["live_checks"][name].get("status")
        print(f"  {name}: artifacts={row.get('status')} live={live_status}")
    print(f"Summary: {output_path}")
    if summary["overall_status"] == "FAIL" or summary["overall_live_status"] == "FAIL":
        return 1
    if summary["overall_status"] != "PASS":
        return 2
    if (args.live or args.ipv6_loopback) and summary["overall_live_status"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
