from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quic_initial_inventory import _initial_headers, inventory


def _initial_packet(dcid: bytes, scid: bytes, body: bytes = b"\x00") -> bytes:
    if len(dcid) > 20 or len(scid) > 20 or len(body) >= 64:
        raise ValueError("test packet fields exceed QUIC short-varint limits")
    return (
        b"\xc0\x00\x00\x00\x01"
        + bytes([len(dcid)]) + dcid
        + bytes([len(scid)]) + scid
        + b"\x00"  # token length
        + bytes([len(body)]) + body
    )


def test_parse_initial_header_connection_ids_and_packet_length():
    packet = _initial_packet(b"orig", b"server-id")
    headers = _initial_headers(packet)
    assert headers == [{
        "version": 1,
        "dcid_hex": b"orig".hex(),
        "dcid_length": 4,
        "scid_hex": b"server-id".hex(),
        "scid_length": 9,
    }]


def test_parse_coalesced_initial_packets():
    packet = _initial_packet(b"first", b"") + _initial_packet(b"changed", b"srv", b"\x01\x02")
    headers = _initial_headers(packet)
    assert [row["dcid_hex"] for row in headers] == [b"first".hex(), b"changed".hex()]


def test_imported_pcaps_show_later_client_dcid_matching_server_scid():
    root = Path(__file__).resolve().parents[3]
    for filename in ("quic_chromium.pcap", "quic_curl.pcap"):
        report = inventory(root / "captures" / "pcaps" / filename)
        assert report["quic_v1_initial_packet_count"] > 0
        assert len(report["flows"]) == 5
        for flow in report["flows"]:
            assert flow["client_to_server_initial_count"] > 0
            assert flow["server_to_client_initial_count"] > 0
            assert flow["first_observed_client_initial_dcid_length"] == 8
            assert len(flow["later_distinct_client_initial_dcids_hex"]) == 1
            assert flow["later_client_dcids_matching_server_initial_scid_hex"] == flow[
                "later_distinct_client_initial_dcids_hex"
            ]
