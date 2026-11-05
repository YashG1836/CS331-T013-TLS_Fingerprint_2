import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from l3_proxy_sanity import classify_paired_streams, main, parse_tshark_fields

FIELDS = (
    "frame.number\tframe.time_epoch\ttcp.stream\tip.src\tipv6.src\ttcp.srcport\tip.dst\tipv6.dst\ttcp.dstport\t"
    "tcp.flags.syn\ttcp.flags.ack\ttcp.seq_raw\ttcp.ack_raw\ttcp.options.mss_val\t"
    "tcp.options.wscale.shift\ttcp.options.sack_perm\ttcp.options.timestamp.tsval\t"
    "tcp.options.timestamp.tsecr\ttcp.window_size_value\tip.ttl\tipv6.hlim\tip.len\t"
    "ipv6.plen\ttcp.len\tframe.len"
)


def _row(frame, stream, src, sport, dst, dport, syn, ack, seq, ackno, mss, ttl):
    values = [
        frame, f"1793712928.{frame:03d}", stream, src, "", sport, dst, "", dport,
        syn, ack, seq, ackno, mss, "10", "0402", "12345", "0", "64240", ttl,
        "", "60", "", "0", "74",
    ]
    return "\t".join(map(str, values))


def _stream(syn_seq, synack_seq, syn_options=(1460, 10, True, True, 64240),
            synack_options=(65495, 7, True, True, 65408), tuple_suffix=""):
    def row(seq, ack, options, src, sport, dst, dport):
        mss, scale, sack, ts, window = options
        return {
            "seq": seq, "ack": ack, "mss": mss, "window_scale": scale,
            "sack_permitted": sack, "timestamp_present": ts, "window": window,
            "src": src + tuple_suffix, "src_port": sport, "dst": dst, "dst_port": dport,
        }
    return {
        "client_syn": row(syn_seq, 0, syn_options, "10.0.0.2", 50000, "203.0.113.8", 443),
        "peer_synack": row(synack_seq, syn_seq + 1, synack_options,
                            "203.0.113.8", 443, "10.0.0.2", 50000),
    }


def test_parse_tshark_syn_and_synack_fields():
    text = "\n".join([
        FIELDS,
        _row(7, 3, "172.17.0.2", 59358, "104.16.124.96", 443, "True", "False", 100, 0, 1460, 64),
        _row(8, 3, "104.16.124.96", 443, "172.17.0.2", 59358, "True", "True", 200, 101, 65495, 63),
    ]) + "\n"
    rows = parse_tshark_fields(text, "container")
    assert len(rows) == 2
    assert rows[0].role == "syn"
    assert rows[0].mss == 1460
    assert rows[1].role == "synack"
    assert rows[1].mss == 65495
    assert rows[1].ttl == 63


def test_same_handshake_with_nat_tuple_change_is_not_termination():
    left = _stream(100, 200)
    right = _stream(100, 200, tuple_suffix="-translated")
    result = classify_paired_streams(
        left, right, same_transaction_confirmed=True, capture_points_bracket_boundary=True
    )
    assert result["classification"] == "same_tcp_handshake_with_tuple_translation"
    assert result["proxy_inference"] == "never_confirm_from_this_comparison_alone"


def test_changed_isns_on_correlated_bracketed_legs_are_not_proxy_confirmation():
    left = _stream(100, 200)
    right = _stream(900, 1200, syn_options=(1460, 8, True, True, 65535))
    result = classify_paired_streams(
        left, right, same_transaction_confirmed=True, capture_points_bracket_boundary=True
    )
    assert result["classification"] == "separate_tcp_legs_or_sequence_rewrite"
    assert result["proxy_inference"] == "never_confirm_from_this_comparison_alone"


def test_lone_mss_or_ttl_difference_cannot_classify_proxy():
    left = _stream(100, 200)
    right = _stream(100, 200)
    right["client_syn"]["ttl"] = 63
    right["peer_synack"]["mss"] = 65495
    result = classify_paired_streams(
        left, right, same_transaction_confirmed=False, capture_points_bracket_boundary=False
    )
    assert result["classification"] == "insufficient_correlation"


def test_missing_syn_or_synack_is_incomplete_capture():
    left = _stream(100, 200)
    right = {"client_syn": _stream(900, 1200)["client_syn"], "peer_synack": None}
    result = classify_paired_streams(
        left, right, same_transaction_confirmed=True, capture_points_bracket_boundary=True
    )
    assert result["classification"] == "incomplete_capture"


def test_ttl_only_difference_does_not_change_tcp_handshake_classification():
    left = _stream(100, 200)
    right = _stream(100, 200)
    right["client_syn"]["ttl"] = 63
    right["peer_synack"]["ttl"] = 62
    result = classify_paired_streams(
        left, right, same_transaction_confirmed=True, capture_points_bracket_boundary=True
    )
    assert result["classification"] == "same_tcp_handshake"


def test_same_sequences_but_changed_options_are_reported_as_rewrite_or_mismatch():
    left = _stream(100, 200)
    right = _stream(100, 200, syn_options=(1460, 8, True, True, 65535))
    result = classify_paired_streams(
        left, right, same_transaction_confirmed=True, capture_points_bracket_boundary=True
    )
    assert result["classification"] == "same_sequence_option_rewrite_or_measurement_mismatch"


def test_packet_length_is_not_used_to_infer_ja4t_or_proxy():
    left = _stream(100, 200)
    right = _stream(100, 200)
    left["client_syn"]["frame_length"] = 74
    right["client_syn"]["frame_length"] = 1514
    result = classify_paired_streams(
        left, right, same_transaction_confirmed=True, capture_points_bracket_boundary=True
    )
    assert result["classification"] == "same_tcp_handshake"


def test_cli_writes_conservative_capture_summary_with_fake_tshark(tmp_path, capsys):
    tshark_output = "\n".join([
        FIELDS,
        _row(7, 3, "172.17.0.2", 59358, "104.16.124.96", 443, "True", "False", 100, 0, 1460, 64),
        _row(8, 3, "104.16.124.96", 443, "172.17.0.2", 59358, "True", "True", 200, 101, 65495, 63),
    ])
    fake_tshark = tmp_path / "tshark"
    fake_tshark.write_text(
        "#!/usr/bin/env python3\nimport sys\n"
        "if '--version' in sys.argv:\n    print('TShark (Wireshark) 4.6.4')\n"
        f"else:\n    print({tshark_output!r})\n",
        encoding="utf-8",
    )
    fake_tshark.chmod(0o755)
    pcap = tmp_path / "sample.pcap"
    pcap.write_bytes(b"synthetic placeholder")
    output = tmp_path / "summary.json"

    assert main([
        "--capture", f"container={pcap}", "--tshark", str(fake_tshark),
        "--output", str(output),
    ]) == 0
    capsys.readouterr()
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["captures"][0]["label"] == "container"
    assert len(data["captures"][0]["streams"]) == 1
    assert data["captures"][0]["streams"]["3"]["same_capture_option_asymmetry"]
    assert "No flows are paired automatically" in data["cross_capture_interpretation"]
