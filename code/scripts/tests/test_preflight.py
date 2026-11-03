from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preflight import parse_tshark_fields


def test_parse_tshark_fields_extracts_abbreviations():
    text = (
        "F\tFrame number\tframe.number\tFT_UINT32\tframe\tBASE_DEC\t0x0\t\n"
        "F\tJA4 fingerprint\ttls.handshake.ja4\tFT_STRING\ttls\t\t0x0\t\n"
        "P\tQUIC\tquic\tTransport layer\n"
    )
    assert parse_tshark_fields(text) == {"frame.number", "tls.handshake.ja4"}


def test_empty_tshark_listing_has_no_fields():
    assert parse_tshark_fields("") == set()
