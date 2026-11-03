#!/usr/bin/env python3
"""Generate deterministic QUIC PCAP impairments and compare C++ with TShark.

All generated variants and raw logs should be directed to the ignored
results/reproduced/ directory. Source PCAPs are only read, never modified.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
import re
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PCAP_MAGICS = {
    b"\xd4\xc3\xb2\xa1": "<",  # little-endian, microseconds
    b"\xa1\xb2\xc3\xd4": ">",  # big-endian, microseconds
    b"\x4d\x3c\xb2\xa1": "<",  # little-endian, nanoseconds
    b"\xa1\xb2\x3c\x4d": ">",  # big-endian, nanoseconds
}
MAX_CAPTURED_FRAME = 64 * 1024 * 1024


@dataclass(frozen=True)
class PcapRecord:
    frame_number: int
    header: bytes
    packet: bytes


@dataclass(frozen=True)
class ClassicPcap:
    global_header: bytes
    byte_order: str
    snap_length: int
    link_type: int
    records: tuple[PcapRecord, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_classic_pcap(path: Path) -> ClassicPcap:
    raw = path.read_bytes()
    if len(raw) < 24:
        raise ValueError(f"{path}: shorter than a classic-PCAP global header")
    byte_order = PCAP_MAGICS.get(raw[:4])
    if byte_order is None:
        raise ValueError(f"{path}: unsupported PCAP magic (PCAPNG is not supported)")
    version_major, version_minor = struct.unpack_from(byte_order + "HH", raw, 4)
    snap_length, link_type = struct.unpack_from(byte_order + "II", raw, 16)
    if version_major != 2 or version_minor > 4:
        raise ValueError(f"{path}: unsupported classic-PCAP version {version_major}.{version_minor}")
    if link_type != 1:
        raise ValueError(f"{path}: only Ethernet (DLT_EN10MB, link type 1) is supported")
    if snap_length == 0 or snap_length > MAX_CAPTURED_FRAME:
        raise ValueError(f"{path}: invalid or excessive snapshot length {snap_length}")

    records: list[PcapRecord] = []
    offset = 24
    while offset < len(raw):
        if len(raw) - offset < 16:
            raise ValueError(f"{path}: truncated record header at byte {offset}")
        header = raw[offset : offset + 16]
        captured_length, original_length = struct.unpack_from(byte_order + "II", header, 8)
        if (captured_length > snap_length or captured_length > MAX_CAPTURED_FRAME
                or captured_length > original_length):
            raise ValueError(f"{path}: invalid captured/original length in record {len(records) + 1}")
        packet_start = offset + 16
        packet_end = packet_start + captured_length
        if packet_end > len(raw):
            raise ValueError(f"{path}: truncated payload in record {len(records) + 1}")
        records.append(PcapRecord(len(records) + 1, header, raw[packet_start:packet_end]))
        offset = packet_end
    return ClassicPcap(raw[:24], byte_order, snap_length, link_type, tuple(records))


def write_classic_pcap(path: Path, pcap: ClassicPcap, records: Iterable[PcapRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(pcap.global_header)
        for record in records:
            stream.write(record.header)
            stream.write(record.packet)


def drop_frame_records(records: Iterable[PcapRecord], frame_numbers: set[int]) -> list[PcapRecord]:
    return [record for record in records if record.frame_number not in frame_numbers]


def truncate_frame_records(
    records: Iterable[PcapRecord], frame_numbers: set[int], truncate_bytes: int, byte_order: str
) -> list[PcapRecord]:
    if truncate_bytes <= 0:
        raise ValueError("truncate_bytes must be positive")
    output: list[PcapRecord] = []
    found: set[int] = set()
    for record in records:
        if record.frame_number not in frame_numbers:
            output.append(record)
            continue
        if len(record.packet) <= truncate_bytes:
            raise ValueError(f"record {record.frame_number} is too short to truncate by {truncate_bytes} bytes")
        packet = record.packet[:-truncate_bytes]
        header = bytearray(record.header)
        # Keep original_length unchanged: this models a snap-length-truncated record.
        struct.pack_into(byte_order + "I", header, 8, len(packet))
        output.append(PcapRecord(record.frame_number, bytes(header), packet))
        found.add(record.frame_number)
    missing = frame_numbers - found
    if missing:
        raise ValueError(f"unknown frame number(s) requested for truncation: {sorted(missing)}")
    return output


def _split_field_values(field: str) -> list[str]:
    return [part.strip() for part in field.split(",") if part.strip()]


def initial_crypto_selector_command(tshark: str, pcap_path: Path) -> list[str]:
    return [
        tshark, "-r", str(pcap_path), "-Y", "quic.crypto.length > 0",
        "-T", "fields", "-E", "occurrence=a", "-E", "aggregator=,",
        "-e", "frame.number", "-e", "quic.long.packet_type",
    ]


def find_initial_crypto_frames(tshark: str, pcap_path: Path) -> list[int]:
    command = initial_crypto_selector_command(tshark, pcap_path)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"TShark could not identify CRYPTO frames:\n{result.stderr.strip()}")
    frames: set[int] = set()
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        packet_types = [value.lower() for value in _split_field_values(fields[1])]
        is_initial = any("initial" in value or value == "0" for value in packet_types)
        if not is_initial:
            continue
        for number in _split_field_values(fields[0]):
            try:
                frames.add(int(number))
            except ValueError:
                raise RuntimeError(f"unexpected frame.number value from TShark: {number!r}") from None
    ordered = sorted(frames)
    if not ordered:
        raise RuntimeError(
            "TShark found no Initial CRYPTO records with filter 'quic.crypto.length > 0'; "
            "check this TShark build's field names and decode"
        )
    return ordered


def make_variants(
    source: Path, output_dir: Path, tshark: str, seed: int, truncate_bytes: int
) -> dict[str, Any]:
    pcap = read_classic_pcap(source)
    if not pcap.records:
        raise ValueError(f"{source}: capture contains no packet records")
    crypto_frames = find_initial_crypto_frames(tshark, source)
    absent = sorted(set(crypto_frames) - {record.frame_number for record in pcap.records})
    if absent:
        raise RuntimeError(f"TShark returned frame numbers absent from classic PCAP: {absent}")
    middle_frame = crypto_frames[len(crypto_frames) // 2]
    every_third = set(crypto_frames[2::3])
    if not every_third:
        every_third = {middle_frame}

    rng = random.Random(seed)
    shuffled = list(pcap.records)
    rng.shuffle(shuffled)
    cases: list[dict[str, Any]] = []

    def save(case_id: str, records: Iterable[PcapRecord], mutation: dict[str, Any]) -> None:
        record_list = list(records)
        variant_path = output_dir / "variants" / f"{case_id}.pcap"
        write_classic_pcap(variant_path, pcap, record_list)
        cases.append({
            "case_id": case_id,
            "path": str(variant_path),
            "sha256": sha256_file(variant_path),
            "packet_records": len(record_list),
            "mutation": mutation,
        })

    save("baseline", pcap.records, {"type": "none"})
    save("reverse-record-order", reversed(pcap.records), {"type": "reverse-record-order"})
    save("shuffle-record-order", shuffled, {"type": "shuffle-record-order", "seed": seed})
    save(
        "drop-one-initial-crypto-record",
        drop_frame_records(pcap.records, {middle_frame}),
        {"type": "drop-initial-crypto-records", "frame_numbers": [middle_frame]},
    )
    save(
        "drop-every-third-initial-crypto-record",
        drop_frame_records(pcap.records, every_third),
        {"type": "drop-initial-crypto-records", "selection": "every third TShark-identified Initial CRYPTO frame",
         "frame_numbers": sorted(every_third)},
    )
    save(
        "truncate-middle-initial-crypto-record",
        truncate_frame_records(pcap.records, {middle_frame}, truncate_bytes, pcap.byte_order),
        {"type": "truncate-captured-record-tail", "frame_numbers": [middle_frame],
         "truncated_bytes": truncate_bytes, "original_length_preserved": True},
    )
    manifest = {
        "schema_version": 1,
        "source_pcap": str(source),
        "source_sha256": sha256_file(source),
        "source_packet_records": len(pcap.records),
        "link_type": pcap.link_type,
        "seed": seed,
        "tshark_crypto_frame_numbers": crypto_frames,
        "tshark_initial_crypto_selector_argv": initial_crypto_selector_command(tshark, source),
        "cases": cases,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cases.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def extract_hex_handshakes_from_jsonraw(document: Any, raw_text: str | None = None) -> list[str]:
    candidates: list[str] = []
    if raw_text is not None:
        pattern = r'"tls\.handshake_raw":\s*\[\s*"([0-9a-fA-F]+)"'
        candidates = re.findall(pattern, raw_text)
    else:
        def visit(node: Any) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "tls.handshake_raw":
                        raw = value[0] if isinstance(value, list) and value else value
                        if isinstance(raw, str):
                            candidates.append(raw.lower())
                    else:
                        visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)

        visit(document)

    hellos: list[str] = []
    for value in candidates:
        normalized = "".join(value.split()).lower()
        if len(normalized) < 8 or len(normalized) % 2:
            continue
        try:
            raw = bytes.fromhex(normalized)
        except ValueError:
            continue
        if raw[0] != 1:
            continue
        declared_length = int.from_bytes(raw[1:4], "big")
        if declared_length == len(raw) - 4:
            hellos.append(normalized)
    return hellos


def parse_extractor_hellos(output: str) -> list[str]:
    hellos: list[str] = []
    for line in output.splitlines():
        if not line.startswith("client_hello_hex="):
            continue
        value = line.split("=", 1)[1].strip().lower()
        if len(value) % 2:
            raise ValueError("extractor emitted odd-length ClientHello hex")
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("extractor emitted non-hex ClientHello data") from exc
        if len(raw) < 4 or raw[0] != 1 or int.from_bytes(raw[1:4], "big") != len(raw) - 4:
            raise ValueError("extractor emitted malformed or incomplete ClientHello framing")
        hellos.append(value)
    return hellos


def compare_hellos(reference: list[str], extracted: list[str]) -> dict[str, Any]:
    ref_counts = collections.Counter(reference)
    ext_counts = collections.Counter(extracted)
    matched = sum((ref_counts & ext_counts).values())
    missed = sum((ref_counts - ext_counts).values())
    extra = sum((ext_counts - ref_counts).values())
    return {
        "reference_count": len(reference),
        "extracted_count": len(extracted),
        "exact_byte_match_count": matched,
        "missed_reference_count": missed,
        "extra_or_nonreference_count": extra,
        "exact_byte_recall": (matched / len(reference)) if reference else None,
        "multiset_equal": ref_counts == ext_counts,
        "reference_sha256": [hashlib.sha256(bytes.fromhex(value)).hexdigest() for value in reference],
        "extracted_sha256": [hashlib.sha256(bytes.fromhex(value)).hexdigest() for value in extracted],
    }


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


def evaluate_variants(manifest: dict[str, Any], work_dir: Path, extractor: str, tshark: str) -> dict[str, Any]:
    extractor_path = _resolve_executable(extractor)
    tshark_path = _resolve_executable(tshark)
    logs_dir = work_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    version_run = subprocess.run([tshark_path, "--version"], capture_output=True, text=True, check=False)
    tshark_version = (version_run.stdout or version_run.stderr).splitlines()[0:1]
    summaries: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        case_id = case["case_id"]
        capture = Path(case["path"]).resolve()
        extractor_argv = [extractor_path, "--pcap", str(capture)]
        extractor_run = subprocess.run(
            extractor_argv, capture_output=True, text=True, check=False
        )
        extractor_log = logs_dir / f"{case_id}_extractor.txt"
        extractor_log.write_text(extractor_run.stdout, encoding="utf-8")
        if extractor_run.stderr:
            (logs_dir / f"{case_id}_extractor.stderr.txt").write_text(extractor_run.stderr, encoding="utf-8")

        tshark_argv = [tshark_path, "-r", str(capture), "-Y", "tls.handshake.type == 1", "-T", "jsonraw"]
        tshark_run = subprocess.run(
            tshark_argv, capture_output=True, text=True, check=False,
        )
        tshark_log = logs_dir / f"{case_id}_tshark.jsonraw"
        tshark_log.write_text(tshark_run.stdout, encoding="utf-8")
        if tshark_run.stderr:
            (logs_dir / f"{case_id}_tshark.stderr.txt").write_text(tshark_run.stderr, encoding="utf-8")

        row: dict[str, Any] = {
            "case_id": case_id,
            "pcap_sha256": case["sha256"],
            "packet_records": case["packet_records"],
            "mutation": case["mutation"],
            "extractor_argv": extractor_argv,
            "tshark_jsonraw_argv": tshark_argv,
            "extractor_exit_code": extractor_run.returncode,
            "tshark_exit_code": tshark_run.returncode,
            "extractor_log": str(extractor_log),
            "extractor_stdout_sha256": hashlib.sha256(extractor_run.stdout.encode("utf-8")).hexdigest(),
            "tshark_jsonraw_log": str(tshark_log),
            "tshark_jsonraw_sha256": hashlib.sha256(tshark_run.stdout.encode("utf-8")).hexdigest(),
        }
        try:
            if tshark_run.returncode != 0:
                raise RuntimeError(tshark_run.stderr.strip() or f"TShark exited {tshark_run.returncode}")
            reference_doc = json.loads(tshark_run.stdout)
            reference = extract_hex_handshakes_from_jsonraw(reference_doc, raw_text=tshark_run.stdout)
            extracted = parse_extractor_hellos(extractor_run.stdout)
            row.update(compare_hellos(reference, extracted))
            row["extractor_incomplete_flow_count"] = len(
                [line for line in extractor_run.stdout.splitlines() if line == "client_hello=incomplete"]
            )
            row["extractor_decrypt_failure_count"] = sum(
                map(int, re.findall(r"decrypt_failures=(\d+)", extractor_run.stdout))
            )
            row["extractor_unsupported_record_count"] = int(
                (re.search(r"unsupported_records=(\d+)", extractor_run.stdout) or [None, "0"])[1]
            )
            row["comparison_status"] = "ok"
        except (ValueError, json.JSONDecodeError, RuntimeError) as exc:
            row["comparison_status"] = "error"
            row["comparison_error"] = str(exc)
        summaries.append(row)

    result = {
        "schema_version": 1,
        "source_pcap": manifest["source_pcap"],
        "source_sha256": manifest["source_sha256"],
        "extractor": extractor_path,
        "tshark": tshark_path,
        "tshark_version_line": tshark_version[0] if tshark_version else "unavailable",
        "python_version": sys.version,
        "tshark_initial_crypto_selector_argv": manifest.get("tshark_initial_crypto_selector_argv"),
        "comparison_basis": "Counter/multiset of complete ClientHello handshake bytes; no arrival-order assumption",
        "results": summaries,
    }
    output = work_dir / "impairment-results.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    result["results_path"] = str(output)
    return result


def run_experiment(args: argparse.Namespace) -> int:
    source = Path(args.input).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"source PCAP not found: {source}")
    manifest = make_variants(source, work_dir, args.tshark, args.seed, args.truncate_bytes)
    result = evaluate_variants(manifest, work_dir, args.extractor, args.tshark)
    print(f"source_sha256={manifest['source_sha256']}")
    print(f"initial_crypto_frame_count={len(manifest['tshark_crypto_frame_numbers'])}")
    for row in result["results"]:
        print(
            f"case={row['case_id']} status={row['comparison_status']} "
            f"reference={row.get('reference_count', 'n/a')} extracted={row.get('extracted_count', 'n/a')} "
            f"matched={row.get('exact_byte_match_count', 'n/a')} "
            f"recall={row.get('exact_byte_recall', 'n/a')} "
            f"missed={row.get('missed_reference_count', 'n/a')} "
            f"extra={row.get('extra_or_nonreference_count', 'n/a')}"
        )
    print(f"results_json={result['results_path']}")
    return 0 if all(row["comparison_status"] == "ok" for row in result["results"]) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="source classic-Ethernet PCAP (never modified)")
    parser.add_argument("--work-dir", required=True, help="output directory; use results/reproduced/<name>")
    parser.add_argument("--extractor", default="build/code/quic/src/quic-fingerprint")
    parser.add_argument("--tshark", default="tshark")
    parser.add_argument("--seed", type=int, default=331)
    parser.add_argument("--truncate-bytes", type=int, default=64)
    parser.set_defaults(func=run_experiment)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        print(f"quic impairment run failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
