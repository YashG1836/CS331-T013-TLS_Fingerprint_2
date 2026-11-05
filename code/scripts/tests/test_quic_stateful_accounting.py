import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quic_impairment import build_parser, parse_extractor_accounting


def test_stateful_cli_flag_is_explicit():
    args = build_parser().parse_args([
        "--input", "capture.pcap", "--work-dir", "work", "--stateful-initial-context"
    ])
    assert args.stateful_initial_context is True


def test_parses_directional_and_alias_accounting_without_merging_packet_buckets():
    output = """initial_packets_total=26
client_initial_packets=16
server_initial_packets=10
client_initial_decrypted=16
server_initial_decrypted=10
client_initial_decrypt_failures=0
server_initial_decrypt_failures=0
client_initial_context_misses=0
server_initial_context_misses=0
dcid_keyed_client_initial_packets=16
dcid_keyed_client_decrypted=10
dcid_keyed_client_decrypt_failures=6
dcid_keyed_client_dcid_buckets=11
switched_dcid_alias_buckets=5
switched_dcid_client_initial_packets=6
connections=5
connection_flow=192.0.2.1:52000->198.51.100.2:443 original_client_initial_dcid=0102 client_initial_packets=4 server_initial_packets=2 client_decrypted_packets=4 server_decrypted_packets=2 client_decrypt_failures=0 server_decrypt_failures=0 decrypt_failures=0 client_context_misses=0 server_context_misses=0 switched_dcid_alias_buckets=1 switched_dcid_client_packets=2
"""
    result = parse_extractor_accounting(output)
    assert result["initial_packets_total"] == 26
    assert result["client_initial_packets"] == 16
    assert result["server_initial_packets"] == 10
    assert result["dcid_keyed_client_decrypted"] == 10
    assert result["dcid_keyed_client_decrypt_failures"] == 6
    assert result["dcid_keyed_client_dcid_buckets"] == 11
    assert result["switched_dcid_alias_buckets"] == 5
    assert result["switched_dcid_client_initial_packets"] == 6
    assert len(result["per_connection"]) == 1
    assert result["per_connection"][0]["switched_dcid_alias_buckets"] == 1
    assert result["per_connection"][0]["switched_dcid_client_packets"] == 2
