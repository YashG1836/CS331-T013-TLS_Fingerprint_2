#pragma once
#include "quic/frame_parser.hpp"
#include <cstddef>
#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <utility>
#include <vector>
namespace quic {
class CryptoReassembly {
 public:
  explicit CryptoReassembly(std::size_t maximum_size = 1U << 20);
  Result<bool> insert(std::uint64_t offset, std::span<const std::uint8_t> data);
  std::optional<Bytes> complete_handshake() const;
  std::size_t contiguous_size() const;
  std::uint64_t observed_extent() const;
  std::optional<std::uint64_t> expected_client_hello_size() const;
  std::vector<std::pair<std::uint64_t, std::uint64_t>> missing_ranges(std::uint64_t limit) const;
 private:
  std::size_t maximum_size_;
  std::map<std::uint64_t, std::uint8_t> bytes_;
};
} // namespace quic
