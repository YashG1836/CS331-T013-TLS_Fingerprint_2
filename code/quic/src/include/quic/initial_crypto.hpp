#pragma once
#include "quic/packet_parser.hpp"
#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string>

namespace quic {
struct InitialKeys {
  std::array<std::uint8_t, 16> key{};
  std::array<std::uint8_t, 12> iv{};
  std::array<std::uint8_t, 16> header_protection_key{};
};
struct DecryptedInitial {
  std::uint64_t packet_number{};
  Bytes plaintext;
  Bytes associated_data;
};
Result<InitialKeys> derive_initial_keys(std::span<const std::uint8_t> destination_connection_id, bool from_client);
Result<DecryptedInitial> decrypt_initial_packet(std::span<const std::uint8_t> datagram,
                                                const LongHeaderPacket& packet,
                                                const InitialKeys& keys,
                                                std::optional<std::uint64_t> largest_received = std::nullopt);
} // namespace quic
