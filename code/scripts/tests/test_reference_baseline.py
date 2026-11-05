import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference_baseline import run_capture_baseline


def executable(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_reference_baseline_records_commands_versions_and_raw_outputs(tmp_path: Path):
    ja4 = executable(
        tmp_path / "ja4",
        """#!/usr/bin/env python3
import json, sys
if sys.argv[1:] == ["--version"]:
    print("ja4 0.18.6")
else:
    print(json.dumps([{"transport": "quic", "ja4": "q13example"}]))
""",
    )
    tshark = executable(
        tmp_path / "tshark",
        """#!/usr/bin/env python3
import sys
args = sys.argv[1:]
if args == ["--version"]:
    print("TShark (Wireshark) 4.4.0")
elif args == ["-G", "fields"]:
    print("F\\tFrame number\\tframe.number\\tFT_UINT32\\tframe\\tBASE_DEC\\t0x0")
    print("F\\tQUIC version\\tquic.version\\tFT_UINT32\\tquic\\tBASE_HEX\\t0x0")
    print("F\\tJA4\\ttls.handshake.ja4\\tFT_STRING\\ttls\\t\\t0x0")
else:
    fields = [args[i + 1] for i, value in enumerate(args[:-1]) if value == "-e"]
    print("\\t".join(fields))
    print("\\t".join("1" for _ in fields))
""",
    )
    capture = tmp_path / "sample.pcap"
    capture.write_bytes(b"controlled test capture bytes")

    result = run_capture_baseline(
        "sample-quic", capture, ja4_executable=str(ja4), tshark_executable=str(tshark)
    )

    assert result["status"] == "commands_completed"
    assert result["capture_sha256"] == hashlib.sha256(capture.read_bytes()).hexdigest()
    assert result["tools"]["ja4_plus"]["version_command"]["stdout"].strip() == "ja4 0.18.6"
    assert result["tools"]["ja4_plus"]["capture_command"]["argv"][1:] == [
        "--json", str(capture.resolve())
    ]
    assert result["tools"]["ja4_plus"]["parsed_json"] == [
        {"transport": "quic", "ja4": "q13example"}
    ]
    assert result["tools"]["tshark"]["fingerprint_fields_available"]["tls.handshake.ja4"]
    assert result["tools"]["tshark"]["parsed_rows"] == [
        {"frame.number": "1", "quic.version": "1", "tls.handshake.ja4": "1"}
    ]
    assert "no fingerprint comparison" in result["interpretation"]


def test_reference_baseline_fails_closed_when_tools_are_missing(tmp_path: Path):
    capture = tmp_path / "capture.pcap"
    capture.write_bytes(b"capture")
    result = run_capture_baseline(
        "missing-tools", capture,
        ja4_executable=str(tmp_path / "missing-ja4"),
        tshark_executable=str(tmp_path / "missing-tshark"),
    )
    assert result["status"] == "tool_or_command_failure"
    assert not result["tools"]["ja4_plus"]["version_command"]["available"]
    assert not result["tools"]["tshark"]["version_command"]["available"]
