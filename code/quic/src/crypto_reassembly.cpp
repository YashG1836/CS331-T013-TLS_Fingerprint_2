#include "quic/crypto_reassembly.hpp"
#include <algorithm>
#include <limits>
namespace quic {
CryptoReassembly::CryptoReassembly(std::size_t maximum_size):maximum_size_(maximum_size){}
Result<bool> CryptoReassembly::insert(std::uint64_t offset,std::span<const std::uint8_t> data) {
  if(offset>maximum_size_ || data.size()>maximum_size_-static_cast<std::size_t>(offset))
    return {std::nullopt,ParseError{"CRYPTO range exceeds configured reassembly limit",static_cast<std::size_t>(std::min<std::uint64_t>(offset,maximum_size_))}};
  for(std::size_t i=0;i<data.size();++i){
    const auto at=offset+static_cast<std::uint64_t>(i); auto found=bytes_.find(at);
    if(found!=bytes_.end()&&found->second!=data[i])return {std::nullopt,ParseError{"conflicting overlapping CRYPTO data",static_cast<std::size_t>(at)}};
  }
  for(std::size_t i=0;i<data.size();++i)bytes_.try_emplace(offset+static_cast<std::uint64_t>(i),data[i]);
  return {true,std::nullopt};
}
std::size_t CryptoReassembly::contiguous_size() const {
  std::size_t n=0; for(const auto& [offset,value]:bytes_){(void)value;if(offset!=n)break;++n;} return n;
}
std::uint64_t CryptoReassembly::observed_extent() const {
  return bytes_.empty() ? 0U : bytes_.rbegin()->first + 1U;
}
std::optional<std::uint64_t> CryptoReassembly::expected_client_hello_size() const {
  if (contiguous_size() < 4U || bytes_.at(0) != 1U) return std::nullopt;
  const std::uint64_t body = (static_cast<std::uint64_t>(bytes_.at(1)) << 16U)
                           | (static_cast<std::uint64_t>(bytes_.at(2)) << 8U)
                           | static_cast<std::uint64_t>(bytes_.at(3));
  return body + 4U;
}
std::vector<std::pair<std::uint64_t, std::uint64_t>>
CryptoReassembly::missing_ranges(std::uint64_t limit) const {
  std::vector<std::pair<std::uint64_t, std::uint64_t>> ranges;
  std::uint64_t cursor = 0;
  for (const auto& [offset, value] : bytes_) {
    (void)value;
    if (offset >= limit) break;
    if (offset > cursor) ranges.emplace_back(cursor, offset);
    cursor = offset + 1U;
  }
  if (cursor < limit) ranges.emplace_back(cursor, limit);
  return ranges;
}
std::optional<Bytes> CryptoReassembly::complete_handshake() const {
  if(contiguous_size()<4)return std::nullopt;
  const auto type=bytes_.at(0);
  const std::uint64_t body=(static_cast<std::uint64_t>(bytes_.at(1))<<16U)|(static_cast<std::uint64_t>(bytes_.at(2))<<8U)|bytes_.at(3);
  const auto total=body+4;
  if(type!=1||total>maximum_size_||total>std::numeric_limits<std::size_t>::max()||contiguous_size()<total)return std::nullopt;
  Bytes result; result.reserve(static_cast<std::size_t>(total));
  for(std::uint64_t i=0;i<total;++i)result.push_back(bytes_.at(i));
  return result;
}
} // namespace quic
