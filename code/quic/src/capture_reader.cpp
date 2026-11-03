#include "quic/capture_reader.hpp"

#include <array>
#include <fstream>
#include <limits>
#include <string>

namespace quic {
namespace {

enum class ByteOrder { Little, Big };

std::uint16_t read_u16(const std::uint8_t* data, ByteOrder order) {
  if (order == ByteOrder::Little) {
    return static_cast<std::uint16_t>(static_cast<std::uint16_t>(data[0]) |
        (static_cast<std::uint16_t>(data[1]) << 8U));
  }
  return static_cast<std::uint16_t>((static_cast<std::uint16_t>(data[0]) << 8U) |
      static_cast<std::uint16_t>(data[1]));
}

std::uint32_t read_u32(const std::uint8_t* data, ByteOrder order) {
  if (order == ByteOrder::Little) {
    return static_cast<std::uint32_t>(data[0]) |
        (static_cast<std::uint32_t>(data[1]) << 8U) |
        (static_cast<std::uint32_t>(data[2]) << 16U) |
        (static_cast<std::uint32_t>(data[3]) << 24U);
  }
  return (static_cast<std::uint32_t>(data[0]) << 24U) |
      (static_cast<std::uint32_t>(data[1]) << 16U) |
      (static_cast<std::uint32_t>(data[2]) << 8U) |
      static_cast<std::uint32_t>(data[3]);
}

std::uint16_t network_u16(const std::uint8_t* data) {
  return static_cast<std::uint16_t>((static_cast<std::uint16_t>(data[0]) << 8U) |
      static_cast<std::uint16_t>(data[1]));
}

bool read_exact(std::ifstream& input, std::uint8_t* dest, std::size_t size) {
  if (size > static_cast<std::size_t>(std::numeric_limits<std::streamsize>::max())) return false;
  input.read(reinterpret_cast<char*>(dest), static_cast<std::streamsize>(size));
  return input.gcount() == static_cast<std::streamsize>(size);
}

void append_udp(PcapReadResult& result, std::size_t frame_number,
                std::uint8_t ip_version, const std::uint8_t* udp,
                std::size_t available) {
  if (available < 8U) {
    ++result.unsupported_records;
    return;
  }
  const std::uint16_t udp_length = network_u16(udp + 4U);
  if (udp_length < 8U || static_cast<std::size_t>(udp_length) > available) {
    ++result.unsupported_records;
    return;
  }
  UdpDatagram datagram;
  datagram.frame_number = frame_number;
  datagram.ip_version = ip_version;
  datagram.source_port = network_u16(udp);
  datagram.destination_port = network_u16(udp + 2U);
  datagram.payload.assign(udp + 8U, udp + udp_length);
  result.udp_datagrams.push_back(std::move(datagram));
}

void parse_frame(PcapReadResult& result, std::size_t frame_number,
                 const Bytes& frame) {
  if (frame.size() < 14U) {
    ++result.unsupported_records;
    return;
  }
  std::size_t offset = 14U;
  const std::uint16_t ether_type = network_u16(frame.data() + 12U);
  if (ether_type == 0x8100U || ether_type == 0x88a8U || ether_type == 0x9100U) {
    ++result.unsupported_records; // VLAN-tagged Ethernet is deliberately unsupported.
    return;
  }

  if (ether_type == 0x0800U) { // IPv4
    if (frame.size() < offset + 20U) {
      ++result.unsupported_records;
      return;
    }
    const std::uint8_t version_ihl = frame[offset];
    const std::size_t header_length = static_cast<std::size_t>(version_ihl & 0x0fU) * 4U;
    if ((version_ihl >> 4U) != 4U || header_length < 20U || frame.size() < offset + header_length) {
      ++result.unsupported_records;
      return;
    }
    const std::uint16_t total_length = network_u16(frame.data() + offset + 2U);
    if (total_length < header_length || frame.size() < offset + total_length) {
      ++result.unsupported_records;
      return;
    }
    const std::uint16_t fragment = network_u16(frame.data() + offset + 6U);
    if ((fragment & 0x3fffU) != 0U) { // MF or non-zero fragment offset.
      ++result.unsupported_records;
      return;
    }
    if (frame[offset + 9U] != 17U) {
      ++result.non_udp_records;
      return;
    }
    const std::size_t udp_offset = offset + header_length;
    const std::size_t ip_payload_length = static_cast<std::size_t>(total_length) - header_length;
    append_udp(result, frame_number, 4U, frame.data() + udp_offset, ip_payload_length);
    return;
  }

  if (ether_type == 0x86ddU) { // IPv6, base header only (no extension chain yet).
    if (frame.size() < offset + 40U || (frame[offset] >> 4U) != 6U) {
      ++result.unsupported_records;
      return;
    }
    const std::uint16_t payload_length = network_u16(frame.data() + offset + 4U);
    if (payload_length == 0U || frame.size() < offset + 40U + payload_length) {
      ++result.unsupported_records; // jumbograms are not supported in this first adapter.
      return;
    }
    if (frame[offset + 6U] != 17U) {
      ++result.unsupported_records; // Includes IPv6 extension headers; do not skip heuristically.
      return;
    }
    append_udp(result, frame_number, 6U, frame.data() + offset + 40U, payload_length);
    return;
  }

  ++result.non_udp_records;
}

} // namespace

Result<PcapReadResult> read_ethernet_udp_pcap(const std::filesystem::path& path) {
  std::ifstream input(path, std::ios::binary);
  if (!input) return {std::nullopt, ParseError{"cannot open PCAP file", 0}};

  std::array<std::uint8_t, 24> global{};
  if (!read_exact(input, global.data(), global.size())) {
    return {std::nullopt, ParseError{"truncated classic-PCAP global header", 0}};
  }

  ByteOrder order{};
  if (global[0] == 0xd4U && global[1] == 0xc3U && global[2] == 0xb2U && global[3] == 0xa1U) {
    order = ByteOrder::Little; // microsecond timestamps
  } else if (global[0] == 0xa1U && global[1] == 0xb2U && global[2] == 0xc3U && global[3] == 0xd4U) {
    order = ByteOrder::Big;
  } else if (global[0] == 0x4dU && global[1] == 0x3cU && global[2] == 0xb2U && global[3] == 0xa1U) {
    order = ByteOrder::Little; // nanosecond timestamps
  } else if (global[0] == 0xa1U && global[1] == 0xb2U && global[2] == 0x3cU && global[3] == 0x4dU) {
    order = ByteOrder::Big;
  } else {
    return {std::nullopt, ParseError{"unsupported PCAP magic (PCAPNG is not supported)", 0}};
  }

  PcapReadResult result;
  result.version_major = read_u16(global.data() + 4U, order);
  result.version_minor = read_u16(global.data() + 6U, order);
  const std::uint32_t snap_length = read_u32(global.data() + 16U, order);
  result.link_type = read_u32(global.data() + 20U, order);
  if (result.version_major != 2U || result.version_minor > 4U) {
    return {std::nullopt, ParseError{"unsupported classic-PCAP version", 4}};
  }
  if (result.link_type != 1U) {
    return {std::nullopt, ParseError{"only Ethernet (DLT_EN10MB) PCAP is supported", 20}};
  }
  if (snap_length == 0U || snap_length > 64U * 1024U * 1024U) {
    return {std::nullopt, ParseError{"invalid or excessive PCAP snapshot length", 16}};
  }

  std::array<std::uint8_t, 16> packet_header{};
  std::size_t frame_number = 0;
  while (true) {
    input.read(reinterpret_cast<char*>(packet_header.data()),
               static_cast<std::streamsize>(packet_header.size()));
    const std::streamsize got = input.gcount();
    if (got == 0 && input.eof()) break;
    if (got != static_cast<std::streamsize>(packet_header.size())) {
      return {std::nullopt, ParseError{"truncated PCAP packet header", frame_number}};
    }
    const std::uint32_t captured_length = read_u32(packet_header.data() + 8U, order);
    const std::uint32_t original_length = read_u32(packet_header.data() + 12U, order);
    if (captured_length > snap_length || captured_length > 64U * 1024U * 1024U ||
        captured_length > original_length) {
      return {std::nullopt, ParseError{"invalid PCAP captured/original packet length", frame_number}};
    }
    Bytes frame(static_cast<std::size_t>(captured_length));
    if (!frame.empty() && !read_exact(input, frame.data(), frame.size())) {
      return {std::nullopt, ParseError{"truncated PCAP packet payload", frame_number}};
    }
    ++frame_number;
    ++result.packet_records;
    parse_frame(result, frame_number, frame);
  }
  return {std::move(result), std::nullopt};
}
} // namespace quic
