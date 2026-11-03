#pragma once
#include "quic/packet_parser.hpp"
#include <cstdint>
#include <string>
#include <vector>
namespace tls {
struct ClientHello {
  std::uint16_t legacy_version{};
  std::vector<std::uint16_t> cipher_suites;
  std::vector<std::uint16_t> extension_types;
  std::vector<std::uint16_t> supported_groups;
  std::vector<std::uint16_t> signature_algorithms;
  std::vector<std::uint16_t> supported_versions;
  std::vector<std::string> alpn_protocols;
  bool has_server_name{};
};
quic::Result<ClientHello> parse_client_hello(std::span<const std::uint8_t> handshake);
} // namespace tls
