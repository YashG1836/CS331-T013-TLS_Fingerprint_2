#pragma once

#include "quic/packet_parser.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <vector>

namespace quic {
struct UdpDatagram {
  std::size_t frame_number{};
  std::uint8_t ip_version{};
  std::array<std::uint8_t, 16> source_address{};
  std::array<std::uint8_t, 16> destination_address{};
  std::uint16_t source_port{};
  std::uint16_t destination_port{};
  Bytes payload;
};

struct PcapReadResult {
  std::uint16_t version_major{};
  std::uint16_t version_minor{};
  std::uint32_t link_type{};
  std::size_t packet_records{};
  std::size_t non_udp_records{};
  std::size_t unsupported_records{};
  std::vector<UdpDatagram> udp_datagrams;
};

// Reads classic PCAP v2.x with Ethernet (DLT_EN10MB) link headers and extracts
// UDP payloads from unfragmented IPv4 and IPv6 frames. PCAPNG, VLAN tags, IP
// fragments, and IPv6 extension-header chains are rejected or counted as
// unsupported; they are never guessed at or silently treated as QUIC.
Result<PcapReadResult> read_ethernet_udp_pcap(const std::filesystem::path& path);
} // namespace quic
