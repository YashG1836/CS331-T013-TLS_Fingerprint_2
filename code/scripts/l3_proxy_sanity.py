#!/usr/bin/env python3
"""Extract TCP SYN profiles and conservatively compare capture vantage points.

This tool reports TCP observations; it does not calculate JA4T/JA4TS and never
infers a proxy from MSS or TTL alone. Use --pair-manifest only for captures
that bracket a documented boundary and contain manually correlated streams.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

FIELDS = (
    "frame.number", "frame.time_epoch", "tcp.stream",
    "ip.src", "ipv6.src", "tcp.srcport", "ip.dst", "ipv6.dst", "tcp.dstport",
    "tcp.flags.syn", "tcp.flags.ack", "tcp.seq_raw", "tcp.ack_raw",
    "tcp.options.mss_val", "tcp.options.wscale.shift", "tcp.options.sack_perm",
    "tcp.options.timestamp.tsval", "tcp.options.timestamp.tsecr",
    "tcp.window_size_value", "ip.ttl", "ipv6.hlim", "ip.len", "ipv6.plen",
    "tcp.len", "frame.len",
)


@dataclass(frozen=True)
class SynObservation:
    capture: str
    stream: str
    role: str
    frame: int
    time_epoch: float | None
    src: str
    src_port: int | None
    dst: str
    dst_port: int | None
    seq: int | None
    ack: int | None
    mss: int | None
    window_scale: int | None
    sack_permitted: bool
    timestamp_present: bool
    window: int | None
    ttl: int | None
    ip_length: int | None
    tcp_length: int | None
    frame_length: int | None

    def option_signature(self) -> tuple[Any, ...]:
        """SYN option/header profile; TTL and ISN are excluded from this tuple."""
        return (
            self.mss,
            self.window_scale,
            self.sack_permitted,
            self.timestamp_present,
            self.window,
        )

    def five_tuple(self) -> tuple[str, int | None, str, int | None]:
        return (self.src, self.src_port, self.dst, self.dst_port)


def _optional_int(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value, 0)
    except ValueError:
        try:
            return int(value, 10)
        except ValueError:
            return None


def _optional_float(value: str) -> float | None:
    try:
        return float(value) if value.strip() else None
    except ValueError:
        return None


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


def tshark_argv(tshark: str, capture_path: Path) -> list[str]:
    return [
        tshark, "-n", "-r", str(capture_path), "-Y", "tcp.flags.syn == 1",
        "-T", "fields", "-E", "header=y", "-E", "separator=/t",
        "-E", "occurrence=f", "-E", "aggregator=,",
        "-o", "tcp.relative_sequence_numbers:FALSE",
        *[arg for field in FIELDS for arg in ("-e", field)],
    ]


def parse_tshark_fields(text: str, capture_label: str) -> list[SynObservation]:
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    rows: list[SynObservation] = []
    for row in reader:
        if not row or not row.get("frame.number", "").strip():
            continue
        if not _truthy(row.get("tcp.flags.syn", "")):
            continue
        ack_flag = _truthy(row.get("tcp.flags.ack", ""))
        src = row.get("ip.src", "").strip() or row.get("ipv6.src", "").strip()
        dst = row.get("ip.dst", "").strip() or row.get("ipv6.dst", "").strip()
        mss = _optional_int(row.get("tcp.options.mss_val", ""))
        scale = _optional_int(row.get("tcp.options.wscale.shift", ""))
        ttl = _optional_int(row.get("ip.ttl", ""))
        if ttl is None:
            ttl = _optional_int(row.get("ipv6.hlim", ""))
        ip_length = _optional_int(row.get("ip.len", ""))
        if ip_length is None:
            ip_length = _optional_int(row.get("ipv6.plen", ""))
        rows.append(SynObservation(
            capture=capture_label,
            stream=row.get("tcp.stream", "").strip() or "unknown",
            role="synack" if ack_flag else "syn",
            frame=_optional_int(row.get("frame.number", "")) or 0,
            time_epoch=_optional_float(row.get("frame.time_epoch", "")),
            src=src,
            src_port=_optional_int(row.get("tcp.srcport", "")),
            dst=dst,
            dst_port=_optional_int(row.get("tcp.dstport", "")),
            seq=_optional_int(row.get("tcp.seq_raw", "")),
            ack=_optional_int(row.get("tcp.ack_raw", "")),
            mss=mss,
            window_scale=scale,
            sack_permitted=bool(row.get("tcp.options.sack_perm", "").strip()),
            timestamp_present=bool(row.get("tcp.options.timestamp.tsval", "").strip()),
            window=_optional_int(row.get("tcp.window_size_value", "")),
            ttl=ttl,
            ip_length=ip_length,
            tcp_length=_optional_int(row.get("tcp.len", "")),
            frame_length=_optional_int(row.get("frame.len", "")),
        ))
    return rows


def _profile_key(observation: SynObservation) -> str:
    return json.dumps(observation.option_signature(), separators=(",", ":"))


def _stream_summaries(observations: list[SynObservation]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, list[SynObservation]]] = collections.defaultdict(
        lambda: {"syn": [], "synack": []}
    )
    for observation in observations:
        grouped[observation.stream][observation.role].append(observation)

    streams: dict[str, dict[str, Any]] = {}
    for stream, roles in sorted(grouped.items()):
        syns = sorted(roles["syn"], key=lambda item: item.frame)
        synacks = sorted(roles["synack"], key=lambda item: item.frame)
        syn = syns[0] if syns else None
        synack = synacks[0] if synacks else None
        differences: list[str] = []
        if syn is not None and synack is not None:
            for name in ("mss", "window_scale", "sack_permitted", "timestamp_present", "window"):
                if getattr(syn, name) != getattr(synack, name):
                    differences.append(name)
        streams[stream] = {
            "client_syn": asdict(syn) if syn else None,
            "peer_synack": asdict(synack) if synack else None,
            "syn_retransmissions_after_first": max(0, len(syns) - 1),
            "synack_retransmissions_after_first": max(0, len(synacks) - 1),
            "same_capture_option_asymmetry": differences,
            "observation_status": "complete_syn_pair" if syn and synack else "one_sided_or_incomplete",
        }
    return streams


def classify_paired_streams(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    same_transaction_confirmed: bool,
    capture_points_bracket_boundary: bool,
) -> dict[str, Any]:
    """Conservative comparison for two manually correlated capture legs."""
    if not same_transaction_confirmed or not capture_points_bracket_boundary:
        return {
            "classification": "insufficient_correlation",
            "reason": "requires a documented paired transaction and capture points bracketing a boundary",
        }
    left_syn = left.get("client_syn")
    left_synack = left.get("peer_synack")
    right_syn = right.get("client_syn")
    right_synack = right.get("peer_synack")
    if not all((left_syn, left_synack, right_syn, right_synack)):
        return {
            "classification": "incomplete_capture",
            "reason": "both SYN and SYN-ACK are required on both capture legs",
        }

    seqs_equal = left_syn["seq"] == right_syn["seq"] and left_synack["seq"] == right_synack["seq"]
    acks_equal = left_syn["ack"] == right_syn["ack"] and left_synack["ack"] == right_synack["ack"]
    options_equal = (
        _dict_option_signature(left_syn) == _dict_option_signature(right_syn)
        and _dict_option_signature(left_synack) == _dict_option_signature(right_synack)
    )
    tuples_equal = (
        _dict_tuple(left_syn) == _dict_tuple(right_syn)
        and _dict_tuple(left_synack) == _dict_tuple(right_synack)
    )
    if seqs_equal and acks_equal and options_equal:
        classification = "same_tcp_handshake"
        if not tuples_equal:
            classification = "same_tcp_handshake_with_tuple_translation"
        reason = "sequence numbers and SYN option profiles agree across the paired captures"
    elif seqs_equal and acks_equal and not options_equal:
        classification = "same_sequence_option_rewrite_or_measurement_mismatch"
        reason = "same sequence and acknowledgment numbers but observed SYN option profiles differ"
    elif seqs_equal or acks_equal:
        classification = "partial_sequence_match_ambiguous"
        reason = "only part of the sequence/acknowledgment tuple agrees across captures"
    else:
        classification = "separate_tcp_legs_or_sequence_rewrite"
        reason = "paired observations have different initial sequence numbers; this is not proxy proof by itself"
    return {
        "classification": classification,
        "reason": reason,
        "client_syn_sequence_equal": left_syn["seq"] == right_syn["seq"],
        "peer_synack_sequence_equal": left_synack["seq"] == right_synack["seq"],
        "acknowledgment_numbers_equal": acks_equal,
        "client_syn_options_equal": _dict_option_signature(left_syn) == _dict_option_signature(right_syn),
        "peer_synack_options_equal": _dict_option_signature(left_synack) == _dict_option_signature(right_synack),
        "four_tuples_equal": tuples_equal,
        "proxy_inference": "never_confirm_from_this_comparison_alone",
    }


def _dict_option_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row.get("mss"), row.get("window_scale"), row.get("sack_permitted"),
            row.get("timestamp_present"), row.get("window"))


def _dict_tuple(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row.get("src"), row.get("src_port"), row.get("dst"), row.get("dst_port"))


def _resolve_executable(value: str) -> str:
    if "/" in value:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"executable not found: {path}")
        return str(path)
    found = shutil.which(value)
    if found is None:
        raise FileNotFoundError(f"executable not found on PATH: {value}")
    return found


def _capture_argument(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("capture must be LABEL=PCAP_PATH")
    label, raw_path = value.split("=", 1)
    label = label.strip()
    path = Path(raw_path).expanduser().resolve()
    if not label or not path.is_file():
        raise argparse.ArgumentTypeError(f"invalid capture label/path: {value!r}")
    return label, path


def analyze_capture(label: str, path: Path, tshark: str) -> dict[str, Any]:
    argv = tshark_argv(tshark, path)
    run = subprocess.run(argv, capture_output=True, text=True, check=False)
    if run.returncode != 0:
        raise RuntimeError(f"TShark failed for {label}: {run.stderr.strip()}")
    observations = parse_tshark_fields(run.stdout, label)
    profile_counts: dict[str, collections.Counter[str]] = {
        "syn": collections.Counter(), "synack": collections.Counter(),
    }
    for observation in observations:
        profile_counts[observation.role][_profile_key(observation)] += 1
    version = subprocess.run([tshark, "--version"], capture_output=True, text=True, check=False)
    version_line = (version.stdout or version.stderr).splitlines()
    return {
        "label": label,
        "pcap": str(path),
        "sha256": _sha256(path),
        "tshark_version": version_line[0] if version_line else "unavailable",
        "tshark_argv": argv,
        "syn_observation_count": len(observations),
        "streams": _stream_summaries(observations),
        "syn_profile_counts": {role: dict(counts) for role, counts in profile_counts.items()},
        "observations": [asdict(observation) for observation in observations],
        "interpretation_limit": "single-capture profiles do not identify a proxy or remote TCP stack",
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_pair_manifest(path: Path, captures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(document.get("pairs"), list):
        raise ValueError("pair manifest must use schema_version 1 and contain a pairs list")
    results: list[dict[str, Any]] = []
    for item in document["pairs"]:
        left_ref = item.get("left", {})
        right_ref = item.get("right", {})
        left_capture = captures.get(left_ref.get("capture", ""))
        right_capture = captures.get(right_ref.get("capture", ""))
        if left_capture is None or right_capture is None:
            raise ValueError(f"pair {item.get('pair_id')!r} references an unknown capture label")
        left = left_capture["streams"].get(str(left_ref.get("stream", "")))
        right = right_capture["streams"].get(str(right_ref.get("stream", "")))
        if left is None or right is None:
            raise ValueError(f"pair {item.get('pair_id')!r} references an unknown tcp.stream")
        result = classify_paired_streams(
            left, right,
            same_transaction_confirmed=item.get("same_transaction_confirmed") is True,
            capture_points_bracket_boundary=item.get("capture_points_bracket_boundary") is True,
        )
        results.append({"pair_id": item.get("pair_id", "unnamed"), **result})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="append", type=_capture_argument, required=True,
                        metavar="LABEL=PCAP", help="label and PCAP/PCAPNG path; may be repeated")
    parser.add_argument("--tshark", default="tshark")
    parser.add_argument("--pair-manifest", type=Path,
                        help="optional JSON manifest for manually correlated streams at paired points")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        tshark = _resolve_executable(args.tshark)
        if len({label for label, _ in args.capture}) != len(args.capture):
            raise ValueError("capture labels must be unique")
        captures = {
            label: analyze_capture(label, path, tshark)
            for label, path in args.capture
        }
        result: dict[str, Any] = {
            "schema_version": 1,
            "python_version": sys.version,
            "captures": list(captures.values()),
            "cross_capture_interpretation": "No flows are paired automatically; use a reviewed pair manifest only for simultaneous captures of a documented transaction.",
        }
        if args.pair_manifest:
            result["paired_comparisons"] = _load_pair_manifest(args.pair_manifest, captures)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
        for label, report in captures.items():
            print(f"{label}: {report['syn_observation_count']} SYN/SYN-ACK observations, "
                  f"{len(report['streams'])} TCP stream(s); no proxy inference from one capture")
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"l3_proxy_sanity: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
