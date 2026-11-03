import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyze import analyze, numbers
from capture import find_capture
from evaluate import load_manifest


def test_track1_capture_ids_are_unique_and_registered():
    entries = [entry for entry in load_manifest()["captures"] if entry.get("capture_recipe")]
    ids = [entry["capture_id"] for entry in entries]
    assert len(ids) == 15
    assert len(ids) == len(set(ids))


def test_each_track1_recipe_has_valid_template_placeholders():
    manifest = load_manifest()
    settings = dict(manifest["lab_settings"])
    settings["output_pcap"] = "captures/reproduced/test.pcap"
    for entry in manifest["captures"]:
        recipe = entry.get("capture_recipe")
        if recipe:
            recipe["command"].format(**settings)
            for command in recipe.get("setup", []):
                command.format(**settings)


def test_capture_lookup_uses_current_manifest_schema():
    manifest = load_manifest()
    assert find_capture(manifest, "quic_chromium")["limitation"] == "L1"
    try:
        find_capture(manifest, "quic-v1-initial-baseline-2026-11-03")
    except ValueError as exc:
        assert "no Track 1 capture recipe" in str(exc)
    else:
        raise AssertionError("Track 2 baseline should not be treated as a Track 1 capture recipe")


def test_numbers_helper_handles_empty_and_multiple_values():
    assert numbers(["1517,1460", "", "x", "3"]) == [1517, 1460, 3]
    assert numbers([]) == []


def _executable(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_fresh_analysis_does_not_call_empty_results_tool_agreement(tmp_path: Path):
    tshark = _executable(tmp_path / "tshark", '''#!/usr/bin/env python3
import sys
args = sys.argv[1:]
if args == ["--version"]:
    print("TShark test")
elif args == ["-G", "fields"]:
    for name in ["frame.number", "tls.handshake.extensions_server_name", "tls.handshake.ja3", "tls.handshake.ja4", "tls.handshake.length", "tcp.segment.count", "quic.crypto.fragment.count", "tls.ech.client_hello_type", "tls.handshake.extensions_key_share_group", "frame.len", "dns.qry.name"]:
        print("F\tTest\t" + name + "\tFT_STRING\ttest\t\t0x0")
elif "-T" in args:
    fields = [args[i + 1] for i, token in enumerate(args[:-1]) if token == "-e"]
    print("\t".join(fields))
''')
    ja4 = _executable(tmp_path / "ja4", '''#!/usr/bin/env python3
import sys
if sys.argv[1:] == ["--version"]:
    print("ja4 test")
''')
    manifest = load_manifest()
    result = analyze(manifest, output_dir=tmp_path / "recomputed", capture_ids={"tls_ipv6"},
                     tshark=str(tshark), ja4=str(ja4), ja4_main="")
    assert result == 0
    rows = json.loads((tmp_path / "recomputed" / "summary.json").read_text())
    assert len(rows) == 1
    assert rows[0]["capture_status"] == "empty"
    assert rows[0]["hellos_tshark"] == 0
    assert rows[0]["tools_agree"] is None
