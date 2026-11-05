#!/usr/bin/env python3
"""Build the quantitative Results section of report/report.md from the committed WSL batch."""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "results" / "track2" / "verification-batch-20261105-105416"
TEMPLATE = ROOT / "report" / "report.template.md"
OUTPUT = ROOT / "report" / "report.md"
START = "<!-- BEGIN GENERATED RESULTS -->"
END = "<!-- END GENERATED RESULTS -->"
TRACES = ("curl", "chromium")
MODES = ("quic-impairment", "quic-stateful")


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def escape_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    top = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join("---" for _ in headers) + "|"
    body = ["| " + " | ".join(escape_cell(v) for v in row) + " |" for row in rows]
    return "\n".join([top, sep, *body])


def load_results(mode: str, trace: str) -> dict:
    return read_json(BATCH / mode / trace / "impairment-results.json")


def source_commit() -> str:
    match = re.search(r"^commit=(.+)$", (BATCH / "environment.txt").read_text(encoding="utf-8"), re.M)
    if not match:
        raise ValueError("environment snapshot has no source commit")
    return match.group(1)


def version_line(prefix: str) -> str:
    text = (BATCH / "environment.txt").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.strip()
    return "not recorded"


def test_counts() -> tuple[str, str]:
    text = (BATCH / "make-test.log").read_text(encoding="utf-8")
    ctest_match = re.search(r"(\d+)/(\d+) Test #\d+:\s+([^\n]+)\s+Passed", text)
    pytest_match = re.search(r"(\d+) passed in ([0-9.]+s)", text)
    test_name = ctest_match.group(3).strip().rstrip(". ") if ctest_match else ""
    ctest = f"{ctest_match.group(1)}/{ctest_match.group(2)} ({test_name})" if ctest_match else "not parsed"
    pytest = f"{pytest_match.group(1)} passed ({pytest_match.group(2)})" if pytest_match else "not parsed"
    return ctest, pytest


def baseline_rows() -> list[list[object]]:
    rows: list[list[object]] = []
    for trace in TRACES:
        result = next(item for item in load_results("quic-stateful", trace)["results"] if item["case_id"] == "baseline")
        accounting = result["extractor_packet_accounting"]
        rows.append([
            trace,
            accounting["connections"],
            accounting["client_initial_packets"],
            f"{accounting['dcid_keyed_client_decrypted']}/{accounting['dcid_keyed_client_decrypt_failures']}",
            f"{accounting['client_initial_decrypted']}/{accounting['client_initial_decrypt_failures']}",
            f"{accounting['server_initial_packets']}, {accounting['server_initial_decrypted']}/{accounting['server_initial_decrypt_failures']}",
            f"{accounting['client_initial_context_misses']}/{accounting['server_initial_context_misses']}",
            f"{accounting['switched_dcid_alias_buckets']}/{accounting['switched_dcid_client_initial_packets']}",
            f"{result['exact_byte_match_count']}/{result['reference_count']}",
            result["missed_reference_count"],
            result["extra_or_nonreference_count"],
            result["multiset_equal"],
        ])
    return rows


def mutation_rows() -> list[list[object]]:
    curl = {item["case_id"]: item for item in load_results("quic-stateful", "curl")["results"]}
    chromium = {item["case_id"]: item for item in load_results("quic-stateful", "chromium")["results"]}
    case_order = list(curl)
    rows = []
    for case in case_order:
        c, h = curl[case], chromium[case]
        rows.append([
            case,
            f"{c['exact_byte_match_count']}/{c['reference_count']}",
            f"{c['missed_reference_count']}/{c['extra_or_nonreference_count']}",
            f"{h['exact_byte_match_count']}/{h['reference_count']}",
            f"{h['missed_reference_count']}/{h['extra_or_nonreference_count']}",
        ])
    return rows


def stateless_totals() -> list[list[object]]:
    rows = []
    for trace in TRACES:
        results = load_results("quic-impairment", trace)["results"]
        reference = sum(item["reference_count"] for item in results)
        matched = sum(item["exact_byte_match_count"] for item in results)
        missed = sum(item["missed_reference_count"] for item in results)
        extra = sum(item["extra_or_nonreference_count"] for item in results)
        rows.append([trace, len(results), reference, matched, missed, extra])
    return rows


def live_rows() -> tuple[list[list[object]], dict]:
    summary = read_json(BATCH / "seven-rows-live.json")
    rows = []
    for name in summary["rows"]:
        artifact = summary["rows"][name]
        live = summary["live_checks"][name]
        rows.append([name, artifact.get("status"), live.get("status"), live.get("reason", live.get("error", ""))])
    return rows, summary


def generated_results() -> str:
    ctest, pytest = test_counts()
    live, summary = live_rows()
    build_rows = [
        ["Source commit", source_commit()],
        ["TShark", version_line("TShark (")],
        ["Compiler", version_line("g++ (")],
        ["OpenSSL", version_line("OpenSSL ")],
        ["Python", version_line("Python ")],
        ["CTest", ctest],
        ["pytest", pytest],
    ]
    sections = [
        "## Quantitative results (generated from the committed batch)",
        "",
        f"Batch source: `results/track2/verification-batch-20261105-105416/`; generated by `report/build_report.py`. The batch was run in WSL against source commit `{source_commit()}` and committed in the later evidence commit. Values below are read from the recorded environment, test log, JSON results, and seven-row JSON; they are not manually reconstructed from prose.",
        "",
        "### Environment and tests",
        "",
        markdown_table(["Item", "Recorded value"], build_rows),
        "",
        "### Captured-order baseline: packet accounting and byte comparison",
        "",
        markdown_table([
            "Trace", "4-tuple associations", "Client Initial packets", "Legacy client decrypts / failures",
            "Stateful client decrypts / failures", "Stateful server packets, decrypts / failures",
            "Context misses client / server", "Alias buckets / alias packets",
            "ClientHellos matched / reference", "Misses", "Extras", "Multiset equal",
        ], baseline_rows()),
        "",
        "The SHA-256 multisets in the per-trace baseline JSON are compared without arrival-order assumptions. `Multiset equal=true` means the stateful C++ output bytes match TShark 4.6.4's ClientHello bytes for that same captured-order PCAP; this is a comparator result, not independent ground truth.",
        "",
        "### Stateful mutation matrix",
        "",
        markdown_table(["Case", "curl matched / reference", "curl misses / extras", "Chromium matched / reference", "Chromium misses / extras"], mutation_rows()),
        "",
        "This matrix makes record-order sensitivity visible: the reversed case has zero extracted ClientHellos in each trace, and the shuffled case misses one per trace. The baseline result does not establish order-independent stateful extraction. The dropped-record/truncated cases are compared against TShark on each corresponding mutated PCAP.",
        "",
        "### Earlier stateless comparison matrix",
        "",
        markdown_table(["Trace", "Cases", "Reference ClientHellos", "Exact byte matches", "Misses", "Extras"], stateless_totals()),
        "",
        "The previous stateless matrix matches the TShark output for all six cases per trace (27/27 each). The every-third-drop case contains two TShark reference hellos, so 2/2 is not recovery of the five baseline hellos.",
        "",
        "### Seven-row verifier",
        "",
        markdown_table(["Row", "Artifact audit", "Requested live check", "Reason / note"], live),
        "",
        f"Overall artifact status: **{summary['overall_status']}**; overall live status: **{summary['overall_live_status']}**. L6's artifact status is `NOT_MEASURED` for public IPv6 egress. The optional local loopback check is a separate control and its recorded failure is not a public-egress measurement.",
        "",
        "Primary output references: `quic-stateful/{curl,chromium}/impairment-results.json`, `quic-impairment/{curl,chromium}/impairment-results.json`, `seven-rows-live.json`, and `make-test.log`.",
    ]
    return "\n".join(sections)


def main() -> int:
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(START) != 1 or template.count(END) != 1:
        raise ValueError("report template must contain exactly one generated-results marker pair")
    if template.index(START) > template.index(END):
        raise ValueError("generated-results markers are out of order")
    content = template.replace(START, generated_results(), 1).replace(END, "", 1)
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(ROOT)} from {BATCH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
