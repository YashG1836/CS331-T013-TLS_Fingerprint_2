from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preflight import baseline_is_ready, parse_tshark_fields


def test_parse_tshark_fields_extracts_abbreviations():
    text = (
        "F\tFrame number\tframe.number\tFT_UINT32\tframe\tBASE_DEC\t0x0\t\n"
        "F\tJA4 fingerprint\ttls.handshake.ja4\tFT_STRING\ttls\t\t0x0\t\n"
        "P\tQUIC\tquic\tTransport layer\n"
    )
    assert parse_tshark_fields(text) == {"frame.number", "tls.handshake.ja4"}


def test_empty_tshark_listing_has_no_fields():
    assert parse_tshark_fields("") == set()


def test_reference_baseline_readiness_requires_all_prerequisites():
    tools = {
        name: {"available": True}
        for name in ("cmake", "compiler", "openssl", "tshark", "ja4", "dumpcap")
    }
    tshark = {"available": True, "has_quic_fields": True}
    interfaces = {"available": True}
    assert baseline_is_ready(tools, tshark, interfaces)

    for missing in ("cmake", "tshark", "ja4", "dumpcap"):
        without_tool = {name: dict(result) for name, result in tools.items()}
        without_tool[missing]["available"] = False
        assert not baseline_is_ready(without_tool, tshark, interfaces)

    assert not baseline_is_ready(tools, {"available": False}, interfaces)
    assert not baseline_is_ready(tools, {"available": True, "has_quic_fields": False}, interfaces)
    assert not baseline_is_ready(tools, tshark, {"available": False})
