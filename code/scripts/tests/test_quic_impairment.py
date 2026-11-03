import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quic_impairment import (
    compare_hellos,
    drop_frame_records,
    extract_hex_handshakes_from_jsonraw,
    make_variants,
    read_classic_pcap,
    truncate_frame_records,
    write_classic_pcap,
)


def _pcap_bytes(*packets: bytes) -> bytes:
    global_header = b"\xd4\xc3\xb2\xa1" + struct.pack("<HHiIII", 2, 4, 0, 0, 65535, 1)
    records = bytearray()
    for index, packet in enumerate(packets, 1):
        records += struct.pack("<IIII", index, 0, len(packet), len(packet))
        records += packet
    return global_header + records


def test_read_and_write_preserve_classic_pcap_records(tmp_path: Path):
    source = tmp_path / "source.pcap"
    source.write_bytes(_pcap_bytes(b"first", b"second", b"third"))
    pcap = read_classic_pcap(source)
    assert pcap.link_type == 1
    assert [record.frame_number for record in pcap.records] == [1, 2, 3]

    reversed_path = tmp_path / "reversed.pcap"
    write_classic_pcap(reversed_path, pcap, reversed(pcap.records))
    reversed_pcap = read_classic_pcap(reversed_path)
    assert [record.packet for record in reversed_pcap.records] == [b"third", b"second", b"first"]


def test_drop_targets_are_one_based_original_frame_numbers(tmp_path: Path):
    source = tmp_path / "source.pcap"
    source.write_bytes(_pcap_bytes(b"one", b"two", b"three"))
    pcap = read_classic_pcap(source)
    kept = drop_frame_records(pcap.records, {2})
    output = tmp_path / "dropped.pcap"
    write_classic_pcap(output, pcap, kept)
    assert [record.packet for record in read_classic_pcap(output).records] == [b"one", b"three"]


def test_truncation_changes_captured_length_only(tmp_path: Path):
    source = tmp_path / "source.pcap"
    source.write_bytes(_pcap_bytes(b"0123456789"))
    pcap = read_classic_pcap(source)
    mutated = truncate_frame_records(pcap.records, {1}, 4, pcap.byte_order)
    output = tmp_path / "truncated.pcap"
    write_classic_pcap(output, pcap, mutated)
    parsed = read_classic_pcap(output)
    assert parsed.records[0].packet == b"012345"
    captured, original = struct.unpack_from("<II", parsed.records[0].header, 8)
    assert captured == 6
    assert original == 10


def test_jsonraw_extracts_only_complete_clienthello_handshakes():
    client_hello = "0100000100"  # type 1, body length 1
    server_hello = "0200000100"
    partial_client_hello = "0100000200"
    document = {
        "_source": {"layers": {
            "tls.handshake_raw": [client_hello, 0, 5],
            "nested": {"tls.handshake_raw": [server_hello, 10, 5]},
            "another": {"tls.handshake_raw": [partial_client_hello, 20, 5]},
        }}
    }
    assert extract_hex_handshakes_from_jsonraw(document) == [client_hello]


def test_variant_generation_is_deterministic_and_preserves_source(tmp_path: Path):
    source = tmp_path / "source.pcap"
    source.write_bytes(_pcap_bytes(b"A" * 100, b"B" * 100, b"C" * 100, b"D" * 100))
    source_before = source.read_bytes()
    tshark = tmp_path / "fake-tshark"
    tshark.write_text("#!/bin/sh\nprintf '1\tInitial\n2\tInitial\n3\tInitial\n4\tInitial\n'\n", encoding="utf-8")
    tshark.chmod(0o755)

    manifest = make_variants(source, tmp_path / "work", str(tshark), seed=17, truncate_bytes=8)
    assert source.read_bytes() == source_before
    assert len(manifest["cases"]) == 6
    assert manifest["tshark_crypto_frame_numbers"] == [1, 2, 3, 4]
    by_id = {case["case_id"]: case for case in manifest["cases"]}
    assert by_id["drop-one-initial-crypto-record"]["mutation"]["frame_numbers"] == [3]
    assert by_id["drop-every-third-initial-crypto-record"]["mutation"]["frame_numbers"] == [3]
    truncated = read_classic_pcap(Path(by_id["truncate-middle-initial-crypto-record"]["path"]))
    assert len(truncated.records[2].packet) == 92
    shuffled_once = Path(by_id["shuffle-record-order"]["path"]).read_bytes()
    manifest_again = make_variants(source, tmp_path / "work2", str(tshark), seed=17, truncate_bytes=8)
    by_id_again = {case["case_id"]: case for case in manifest_again["cases"]}
    assert shuffled_once == Path(by_id_again["shuffle-record-order"]["path"]).read_bytes()


def test_comparison_uses_multiplicity_not_only_a_set():
    hello = "0100000100"
    result = compare_hellos([hello, hello], [hello])
    assert result["exact_byte_match_count"] == 1
    assert result["missed_reference_count"] == 1
    assert result["extra_or_nonreference_count"] == 0
    assert result["exact_byte_recall"] == 0.5
    assert result["multiset_equal"] is False
