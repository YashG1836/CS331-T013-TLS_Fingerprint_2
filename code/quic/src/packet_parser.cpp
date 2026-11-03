#include "quic/packet_parser.hpp"
#include <limits>

namespace quic {
namespace {
Result<std::uint64_t> read_var(std::span<const std::uint8_t> in, std::size_t& pos) {
  auto r = decode_varint(in, pos);
  if (!r) return {std::nullopt, r.error};
  pos += r.value->encoded_length;
  return {r.value->value, std::nullopt};
}
Result<Bytes> read_cid(std::span<const std::uint8_t> in, std::size_t& pos) {
  if (pos >= in.size()) return {std::nullopt, ParseError{"missing connection-id length", pos}};
  const auto n = static_cast<std::size_t>(in[pos++]);
  if (n > 20) return {std::nullopt, ParseError{"connection ID exceeds 20 bytes", pos - 1}};
  if (n > in.size() - pos) return {std::nullopt, ParseError{"truncated connection ID", pos}};
  Bytes out(in.begin() + static_cast<std::ptrdiff_t>(pos), in.begin() + static_cast<std::ptrdiff_t>(pos + n));
  pos += n;
  return {std::move(out), std::nullopt};
}
}
Result<VarInt> decode_varint(std::span<const std::uint8_t> in, std::size_t offset) {
  if (offset >= in.size()) return {std::nullopt, ParseError{"truncated variable integer", offset}};
  const auto first = in[offset];
  const std::size_t n = std::size_t{1} << (first >> 6U);
  if (n > in.size() - offset) return {std::nullopt, ParseError{"truncated variable integer", offset}};
  std::uint64_t value = static_cast<std::uint64_t>(first & 0x3fU);
  for (std::size_t i = 1; i < n; ++i) value = (value << 8U) | in[offset + i];
  return {VarInt{value, n}, std::nullopt};
}
Result<std::vector<LongHeaderPacket>> parse_long_header_datagram(std::span<const std::uint8_t> data) {
  std::vector<LongHeaderPacket> packets;
  std::size_t pos = 0;
  while (pos < data.size()) {
    const auto start = pos;
    if (data.size() - pos < 6) return {std::nullopt, ParseError{"truncated long header", pos}};
    const auto first = data[pos++];
    if ((first & 0x80U) == 0) return {std::nullopt, ParseError{"short-header packet encountered; only long headers are supported", start}};
    std::uint32_t version = (static_cast<std::uint32_t>(data[pos]) << 24U) |
                            (static_cast<std::uint32_t>(data[pos + 1]) << 16U) |
                            (static_cast<std::uint32_t>(data[pos + 2]) << 8U) | data[pos + 3];
    pos += 4;
    auto dcid = read_cid(data, pos); if (!dcid) return {std::nullopt, dcid.error};
    auto scid = read_cid(data, pos); if (!scid) return {std::nullopt, scid.error};
    LongHeaderPacket p;
    p.version = version; p.destination_connection_id = std::move(*dcid.value);
    p.source_connection_id = std::move(*scid.value); p.packet_start = start;
    if (version == 0) {
      p.type = PacketType::VersionNegotiation; p.packet_end = data.size(); packets.push_back(std::move(p)); break;
    }
    // This implementation deliberately supports QUIC v1 only. The v1 packet type is in bits 4..5.
    if (version != 1) return {std::nullopt, ParseError{"unsupported QUIC version (v1 only)", start + 1}};
    switch ((first >> 4U) & 0x03U) {
      case 0: p.type = PacketType::Initial; break;
      case 1: p.type = PacketType::ZeroRtt; break;
      case 2: p.type = PacketType::Handshake; break;
      default: p.type = PacketType::Retry; break;
    }
    if (p.type == PacketType::Retry) {
      if (data.size() - pos < 16) return {std::nullopt, ParseError{"truncated Retry integrity tag", pos}};
      p.packet_end = data.size(); packets.push_back(std::move(p)); break;
    }
    if (p.type == PacketType::Initial) {
      p.token_offset = pos;
      auto token_len = read_var(data, pos); if (!token_len) return {std::nullopt, token_len.error};
      if (*token_len.value > data.size() - pos) return {std::nullopt, ParseError{"truncated Initial token", pos}};
      p.token_length = static_cast<std::size_t>(*token_len.value); pos += p.token_length;
    }
    p.length_field_offset = pos;
    auto length = read_var(data, pos); if (!length) return {std::nullopt, length.error};
    p.protected_length = *length.value;
    p.packet_number_offset = pos;
    if (p.protected_length > data.size() - pos) return {std::nullopt, ParseError{"packet length exceeds remaining datagram", pos}};
    if (p.protected_length > std::numeric_limits<std::size_t>::max()) return {std::nullopt, ParseError{"packet length is not representable", pos}};
    p.packet_end = pos + static_cast<std::size_t>(p.protected_length);
    if (p.packet_end == pos) return {std::nullopt, ParseError{"empty protected packet", pos}};
    packets.push_back(std::move(p));
    pos = packets.back().packet_end;
  }
  return {std::move(packets), std::nullopt};
}
const char* packet_type_name(PacketType t) {
  switch(t) { case PacketType::Initial:return "initial"; case PacketType::ZeroRtt:return "0-rtt"; case PacketType::Handshake:return "handshake"; case PacketType::Retry:return "retry"; case PacketType::VersionNegotiation:return "version-negotiation"; default:return "unknown"; }
}
} // namespace quic
