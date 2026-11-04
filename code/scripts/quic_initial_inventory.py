#!/usr/bin/env python3
"""Summarize QUIC v1 Initial connection IDs by packet direction from classic Ethernet PCAP.

This is a header-only inventory: it does not decrypt Initial payloads or infer a proxy.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any

from quic_impairment import read_classic_pcap


def _varint(data: bytes, offset: int) -> tuple[int, int]:
    if offset >= len(data):
        raise ValueError("truncated QUIC variable-length integer")
    size = 1 << (data[offset] >> 6)
    end = offset + size
    if end > len(data):
        raise ValueError("truncated QUIC variable-length integer")
    value = data[offset] & 0x3F
    for byte in data[offset + 1:end]:
        value = (value << 8) | byte
    return value, end


def _ethernet_udp(packet: bytes) -> tuple[str, str, int, int, bytes] | None:
    if len(packet) < 14:
        return None
    offset = 14
    ethertype = struct.unpack_from("!H", packet, 12)[0]
    while ethertype in (0x8100, 0x88A8, 0x9100):
        if len(packet) < offset + 4:
            return None
        ethertype = struct.unpack_from("!H", packet, offset + 2)[0]
        offset += 4

    if ethertype == 0x0800:  # IPv4
        if len(packet) < offset + 20 or packet[offset] >> 4 != 4:
            return None
        header_length = (packet[offset] & 0x0F) * 4
        if header_length < 20 or len(packet) < offset + header_length:
            return None
        if packet[offset + 9] != 17:
            return None
        fragment = struct.unpack_from("!H", packet, offset + 6)[0]
        if fragment & 0x1FFF:  # non-initial IPv4 fragment
            return None
        total_length = struct.unpack_from("!H", packet, offset + 2)[0]
        end = min(len(packet), offset + total_length)
        source = ".".join(str(value) for value in packet[offset + 12:offset + 16])
        destination = ".".join(str(value) for value in packet[offset + 16:offset + 20])
        udp_offset = offset + header_length
    elif ethertype == 0x86DD:  # IPv6 base header; extension headers are intentionally out of scope
        if len(packet) < offset + 40 or packet[offset] >> 4 != 6 or packet[offset + 6] != 17:
            return None
        payload_length = struct.unpack_from("!H", packet, offset + 4)[0]
        end = min(len(packet), offset + 40 + payload_length)
        source = str(ipaddress.IPv6Address(packet[offset + 8:offset + 24]))
        destination = str(ipaddress.IPv6Address(packet[offset + 24:offset + 40]))
        udp_offset = offset + 40
    else:
        return None

    if udp_offset + 8 > end:
        return None
    source_port, destination_port, udp_length = struct.unpack_from("!HHH", packet, udp_offset)
    if udp_length < 8 or udp_offset + udp_length > end:
        return None
    return (source, destination, source_port, destination_port,
            packet[udp_offset + 8:udp_offset + udp_length])


def _initial_headers(datagram: bytes) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    offset = 0
    while offset + 7 <= len(datagram):
        first = datagram[offset]
        if not first & 0x80:
            break
        version = int.from_bytes(datagram[offset + 1:offset + 5], "big")
        cursor = offset + 5
        dcid_length = datagram[cursor]
        cursor += 1
        if dcid_length > 20 or cursor + dcid_length + 1 > len(datagram):
            break
        dcid = datagram[cursor:cursor + dcid_length]
        cursor += dcid_length
        scid_length = datagram[cursor]
        cursor += 1
        if scid_length > 20 or cursor + scid_length > len(datagram):
            break
        scid = datagram[cursor:cursor + scid_length]
        cursor += scid_length
        packet_type = (first >> 4) & 0x03

        if version != 1 or packet_type != 0:  # only QUIC v1 Initial
            break
        try:
            token_length, cursor = _varint(datagram, cursor)
            cursor += token_length
            packet_length, cursor = _varint(datagram, cursor)
        except ValueError:
            break
        packet_end = cursor + packet_length
        if packet_end > len(datagram):
            break
        packets.append({
            "version": version,
            "dcid_hex": dcid.hex(),
            "dcid_length": len(dcid),
            "scid_hex": scid.hex(),
            "scid_length": len(scid),
        })
        offset = packet_end
    return packets


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(path: Path) -> dict[str, Any]:
    pcap = read_classic_pcap(path)
    packets: list[dict[str, Any]] = []
    flows: dict[tuple[str, int, str, int], list[dict[str, Any]]] = defaultdict(list)
    udp_datagrams = 0
    for record in pcap.records:
        decoded = _ethernet_udp(record.packet)
        if decoded is None:
            continue
        source, destination, source_port, destination_port, payload = decoded
        udp_datagrams += 1
        if destination_port == 443:
            direction = "client_to_server_candidate"
            client, client_port, server, server_port = source, source_port, destination, destination_port
        elif source_port == 443:
            direction = "server_to_client_candidate"
            client, client_port, server, server_port = destination, destination_port, source, source_port
        else:
            direction = "other_udp_direction"
            client, client_port, server, server_port = source, source_port, destination, destination_port
        for packet in _initial_headers(payload):
            row = {
                "frame_number": record.frame_number,
                "udp_source": source,
                "udp_source_port": source_port,
                "udp_destination": destination,
                "udp_destination_port": destination_port,
                "direction_candidate": direction,
                **packet,
            }
            packets.append(row)
            flows[(client, client_port, server, server_port)].append(row)

    flow_rows: list[dict[str, Any]] = []
    for (client, client_port, server, server_port), observations in sorted(flows.items()):
        client_packets = [row for row in observations if row["direction_candidate"] == "client_to_server_candidate"]
        server_packets = [row for row in observations if row["direction_candidate"] == "server_to_client_candidate"]
        first_client_dcid = client_packets[0]["dcid_hex"] if client_packets else None
        post_first_dcids = sorted({row["dcid_hex"] for row in client_packets[1:]
                                   if row["dcid_hex"] != first_client_dcid})
        server_scids = {row["scid_hex"] for row in server_packets}
        flow_rows.append({
            "client_endpoint": f"{client}:{client_port}",
            "server_endpoint": f"{server}:{server_port}",
            "client_to_server_initial_count": len(client_packets),
            "server_to_client_initial_count": len(server_packets),
            "first_observed_client_initial_dcid_hex": first_client_dcid,
            "first_observed_client_initial_dcid_length": (
                client_packets[0]["dcid_length"] if client_packets else None
            ),
            "later_distinct_client_initial_dcids_hex": post_first_dcids,
            "later_client_dcids_matching_server_initial_scid_hex": sorted(
                set(post_first_dcids) & server_scids
            ),
            "server_initial_dcids_hex": sorted({row["dcid_hex"] for row in server_packets}),
            "server_initial_scids_hex": sorted(server_scids),
            "frame_numbers": [row["frame_number"] for row in observations],
        })

    version_major, version_minor = struct.unpack_from(pcap.byte_order + "HH", pcap.global_header, 4)
    return {
        "schema_version": 1,
        "input_pcap": str(path),
        "input_sha256": _sha256(path),
        "pcap_version": f"{version_major}.{version_minor}",
        "link_type": pcap.link_type,
        "packet_record_count": len(pcap.records),
        "udp_datagram_count": udp_datagrams,
        "quic_v1_initial_packet_count": len(packets),
        "flows": flow_rows,
        "initial_packet_headers": packets,
        "scope_limit": "Classic Ethernet PCAP; UDP; QUIC v1 long-header Initials only. Direction labels use UDP port 443 as a heuristic, not authenticated endpoint roles. No payload decryption.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True, metavar="PCAP")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = {"schema_version": 1,
                  "captures": [inventory(path.expanduser()) for path in args.input]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
        return 0
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
