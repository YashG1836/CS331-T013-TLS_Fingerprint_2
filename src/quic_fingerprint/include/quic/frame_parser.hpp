#pragma once
#include "quic/packet_parser.hpp"
#include <span>
#include <string>
#include <vector>
namespace quic {
struct CryptoFrame { std::uint64_t offset{}; Bytes data; };
struct FrameParseResult { std::vector<CryptoFrame> crypto_frames; std::size_t frames_seen{}; };
Result<FrameParseResult> parse_initial_frames(std::span<const std::uint8_t> plaintext);
} // namespace quic
