#pragma once
#include "quic/frame_parser.hpp"
#include <map>
#include <optional>
#include <string>
namespace quic {
class CryptoReassembly {
 public:
  explicit CryptoReassembly(std::size_t maximum_size = 1U << 20);
  Result<bool> insert(std::uint64_t offset, std::span<const std::uint8_t> data);
  std::optional<Bytes> complete_handshake() const;
  std::size_t contiguous_size() const;
 private:
  std::size_t maximum_size_;
  std::map<std::uint64_t, std::uint8_t> bytes_;
};
} // namespace quic
