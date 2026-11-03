#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace quic {
using Bytes = std::vector<std::uint8_t>;

enum class PacketType { Initial, ZeroRtt, Handshake, Retry, VersionNegotiation, Unknown };
struct LongHeaderPacket {
  PacketType type{PacketType::Unknown};
  std::uint32_t version{};
  Bytes destination_connection_id;
  Bytes source_connection_id;
  std::size_t packet_start{};
  std::size_t packet_end{}; // exclusive; may be the remainder of a datagram for VN/Retry
  std::size_t packet_number_offset{};
  std::size_t token_offset{};
  std::size_t token_length{};
  std::size_t length_field_offset{};
  std::uint64_t protected_length{};
};
struct ParseError { std::string message; std::size_t offset{}; };
template <typename T> struct Result {
  std::optional<T> value;
  std::optional<ParseError> error;
  explicit operator bool() const { return value.has_value(); }
};

struct VarInt { std::uint64_t value{}; std::size_t encoded_length{}; };
Result<VarInt> decode_varint(std::span<const std::uint8_t> input, std::size_t offset);
Result<std::vector<LongHeaderPacket>> parse_long_header_datagram(std::span<const std::uint8_t> datagram);
const char* packet_type_name(PacketType type);
} // namespace quic
