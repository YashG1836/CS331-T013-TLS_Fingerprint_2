#include "quic/capture_reader.hpp"
#include "quic/crypto_reassembly.hpp"
#include "quic/frame_parser.hpp"
#include "quic/initial_context.hpp"
#include "quic/initial_crypto.hpp"
#include "quic/packet_parser.hpp"
#include "tls/client_hello.hpp"

#include <cctype>
#include <cstdint>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace {
quic::Result<quic::Bytes> from_hex(const std::string& text) {
  quic::Bytes out;
  int high = -1;
  for (std::size_t i = 0; i < text.size(); ++i) {
    const unsigned char ch = static_cast<unsigned char>(text[i]);
    if (std::isspace(ch)) continue;
    int value = -1;
    if (ch >= '0' && ch <= '9') value = ch - '0';
    else if (ch >= 'a' && ch <= 'f') value = ch - 'a' + 10;
    else if (ch >= 'A' && ch <= 'F') value = ch - 'A' + 10;
    else return {std::nullopt, quic::ParseError{"input contains a non-hex character", i}};
    if (high < 0) high = value;
    else {
      out.push_back(static_cast<std::uint8_t>((high << 4) | value));
      high = -1;
    }
  }
  if (high >= 0) return {std::nullopt, quic::ParseError{"hex input has an odd number of digits", text.size()}};
  return {std::move(out), std::nullopt};
}

void print_hex(const quic::Bytes& bytes) {
  static constexpr char digits[] = "0123456789abcdef";
  for (const auto byte : bytes) {
    std::cout << digits[byte >> 4U] << digits[byte & 0x0fU];
  }
}

std::string to_hex(const quic::Bytes& bytes) {
  static constexpr char digits[] = "0123456789abcdef";
  std::string out;
  out.reserve(bytes.size() * 2U);
  for (const auto byte : bytes) {
    out.push_back(digits[byte >> 4U]);
    out.push_back(digits[byte & 0x0fU]);
  }
  return out;
}

std::string format_ranges(
    const std::vector<std::pair<std::uint64_t, std::uint64_t>>& ranges) {
  if (ranges.empty()) return "none";
  std::string out;
  for (const auto& [begin, end] : ranges) {
    if (!out.empty()) out += ",";
    out += "[" + std::to_string(begin) + "," + std::to_string(end) + ")";
  }
  return out;
}

struct FlowState {
  quic::CryptoReassembly crypto;
  std::optional<std::uint64_t> largest_packet_number;
  std::size_t initial_packets{};
  std::size_t decrypted_packets{};
  std::size_t decrypt_failures{};
  std::size_t frame_parse_failures{};
  std::size_t reassembly_failures{};
  std::size_t crypto_frames{};
};

struct BaselineDcidState {
  std::optional<std::uint64_t> largest_packet_number;
  std::size_t initial_packets{};
  std::size_t decrypted_packets{};
  std::size_t decrypt_failures{};
};

struct StatefulFlowState {
  std::map<quic::Bytes, BaselineDcidState> dcid_keyed_baseline;
  quic::CryptoReassembly client_crypto;
  std::optional<std::uint64_t> largest_client_packet_number;
  std::optional<std::uint64_t> largest_server_packet_number;
  std::size_t client_initial_packets{};
  std::size_t server_initial_packets{};
  std::size_t client_decrypted_packets{};
  std::size_t server_decrypted_packets{};
  std::size_t client_decrypt_failures{};
  std::size_t server_decrypt_failures{};
  std::size_t client_context_misses{};
  std::size_t server_context_misses{};
  std::size_t frame_parse_failures{};
  std::size_t reassembly_failures{};
  std::size_t crypto_frames{};
};

int process_pcap(const std::string& path, std::uint16_t destination_port) {
  const auto capture = quic::read_ethernet_udp_pcap(path);
  if (!capture) {
    std::cerr << "PCAP read failed: " << capture.error->message << " at " << capture.error->offset << "\n";
    return 1;
  }
  std::cout << "pcap_version=" << capture.value->version_major << "." << capture.value->version_minor
            << " link_type=" << capture.value->link_type
            << " packet_records=" << capture.value->packet_records
            << " udp_datagrams=" << capture.value->udp_datagrams.size()
            << " non_udp_records=" << capture.value->non_udp_records
            << " unsupported_records=" << capture.value->unsupported_records << "\n";

  std::map<std::string, FlowState> flows;
  std::size_t non_matching_port = 0;
  std::size_t non_quic_datagrams = 0;
  std::size_t malformed_quic_datagrams = 0;
  for (const auto& datagram : capture.value->udp_datagrams) {
    if (datagram.destination_port != destination_port) {
      ++non_matching_port;
      continue;
    }
    if (datagram.payload.empty() || (datagram.payload.front() & 0xc0U) != 0xc0U) {
      ++non_quic_datagrams;
      continue;
    }
    const auto packets = quic::parse_long_header_datagram(datagram.payload);
    if (!packets) {
      ++malformed_quic_datagrams;
      continue;
    }
    for (const auto& packet : *packets.value) {
      if (packet.type != quic::PacketType::Initial || packet.version != 1U) continue;
      if (flows.size() >= 4096U && !flows.contains(to_hex(packet.destination_connection_id))) continue;
      auto& state = flows[to_hex(packet.destination_connection_id)];
      ++state.initial_packets;
      const auto keys = quic::derive_initial_keys(packet.destination_connection_id, true);
      if (!keys) {
        ++state.decrypt_failures;
        continue;
      }
      const auto decrypted = quic::decrypt_initial_packet(datagram.payload, packet, *keys.value,
                                                           state.largest_packet_number);
      if (!decrypted) {
        ++state.decrypt_failures;
        continue;
      }
      ++state.decrypted_packets;
      if (!state.largest_packet_number || decrypted.value->packet_number > *state.largest_packet_number) {
        state.largest_packet_number = decrypted.value->packet_number;
      }
      const auto frames = quic::parse_initial_frames(decrypted.value->plaintext);
      if (!frames) {
        ++state.frame_parse_failures;
        continue;
      }
      for (const auto& frame : frames.value->crypto_frames) {
        ++state.crypto_frames;
        if (!state.crypto.insert(frame.offset, frame.data)) ++state.reassembly_failures;
      }
    }
  }

  std::cout << "non_matching_destination_port=" << non_matching_port
            << " non_quic_datagrams=" << non_quic_datagrams
            << " malformed_quic_datagrams=" << malformed_quic_datagrams
            << " initial_flows=" << flows.size() << "\n";
  std::size_t complete_count = 0;
  for (const auto& [dcid, state] : flows) {
    std::cout << "flow_dcid=" << (dcid.empty() ? "(empty)" : dcid)
              << " initial_packets=" << state.initial_packets
              << " decrypted_packets=" << state.decrypted_packets
              << " decrypt_failures=" << state.decrypt_failures
              << " frame_parse_failures=" << state.frame_parse_failures
              << " reassembly_failures=" << state.reassembly_failures
              << " crypto_frames=" << state.crypto_frames
              << " contiguous_crypto_bytes=" << state.crypto.contiguous_size() << "\n";
    const auto handshake = state.crypto.complete_handshake();
    if (!handshake) {
      const auto expected = state.crypto.expected_client_hello_size();
      const auto extent = state.crypto.observed_extent();
      const auto range_limit = expected.value_or(extent);
      std::cout << "client_hello=incomplete\n"
                << "client_hello_expected_bytes=";
      if (expected) std::cout << *expected;
      else std::cout << "unknown";
      std::cout << "\ncrypto_observed_extent_bytes=" << extent
                << "\ncrypto_missing_ranges_scope="
                << (expected ? "expected_client_hello" : "observed_extent_only")
                << "\ncrypto_missing_ranges="
                << format_ranges(state.crypto.missing_ranges(range_limit)) << "\n";
      continue;
    }
    const auto hello = tls::parse_client_hello(*handshake);
    if (!hello) {
      std::cout << "client_hello=parse_error message=" << hello.error->message
                << " offset=" << hello.error->offset << "\n";
      continue;
    }
    ++complete_count;
    std::cout << "client_hello=complete\n"
              << "client_hello_bytes=" << handshake->size() << "\n"
              << "legacy_version=0x" << std::hex << hello.value->legacy_version << std::dec << "\n"
              << "cipher_suite_count=" << hello.value->cipher_suites.size() << "\n"
              << "extension_count=" << hello.value->extension_types.size() << "\n"
              << "supported_group_count=" << hello.value->supported_groups.size() << "\n"
              << "signature_algorithm_count=" << hello.value->signature_algorithms.size() << "\n"
              << "has_sni=" << (hello.value->has_server_name ? "true" : "false") << "\n"
              << "client_hello_hex=";
    print_hex(*handshake);
    std::cout << "\n";
  }
  std::cout << "complete_client_hellos=" << complete_count << "\n";
  return complete_count > 0U ? 0 : 1;
}

int process_pcap_stateful(const std::string& path, std::uint16_t service_port) {
  const auto capture = quic::read_ethernet_udp_pcap(path);
  if (!capture) {
    std::cerr << "PCAP read failed: " << capture.error->message << " at " << capture.error->offset << "\n";
    return 1;
  }
  std::cout << "pcap_version=" << capture.value->version_major << "." << capture.value->version_minor
            << " link_type=" << capture.value->link_type
            << " packet_records=" << capture.value->packet_records
            << " udp_datagrams=" << capture.value->udp_datagrams.size()
            << " non_udp_records=" << capture.value->non_udp_records
            << " unsupported_records=" << capture.value->unsupported_records << "\n";
  std::cout << "initial_context_mode=stateful-original-dcid-with-server-scid-aliases\n";

  quic::InitialContextAssociator associations;
  std::map<quic::InitialFlowKey, StatefulFlowState> flows;
  std::size_t client_initial_packets = 0;
  std::size_t server_initial_packets = 0;
  std::size_t client_decrypted_packets = 0;
  std::size_t server_decrypted_packets = 0;
  std::size_t client_decrypt_failures = 0;
  std::size_t server_decrypt_failures = 0;
  std::size_t client_context_misses = 0;
  std::size_t server_context_misses = 0;
  std::size_t dcid_keyed_client_decrypted = 0;
  std::size_t dcid_keyed_client_decrypt_failures = 0;
  std::size_t retry_packets_observed = 0;
  std::size_t malformed_quic_datagrams = 0;

  for (const auto& datagram : capture.value->udp_datagrams) {
    const bool client_port_match = datagram.destination_port == service_port;
    const bool server_port_match = datagram.source_port == service_port;
    if (!client_port_match && !server_port_match) continue;
    if (datagram.payload.empty() || (datagram.payload.front() & 0xc0U) != 0xc0U) continue;
    const auto packets = quic::parse_long_header_datagram(datagram.payload);
    if (!packets) {
      ++malformed_quic_datagrams;
      continue;
    }
    for (const auto& packet : *packets.value) {
      if (packet.type == quic::PacketType::Retry && server_port_match) {
        ++retry_packets_observed;
        continue;  // Retry integrity validation/state transition is outside this v1 scope.
      }
      if (packet.type != quic::PacketType::Initial || packet.version != 1U) continue;

      auto observation = associations.observe(datagram, packet, service_port);
      if (observation.direction == quic::InitialDirection::ClientToServer) {
        ++client_initial_packets;
      } else if (observation.direction == quic::InitialDirection::ServerToClient) {
        ++server_initial_packets;
      } else {
        continue;
      }
      if (!observation.flow) continue;

      auto& state = flows[*observation.flow];
      if (observation.direction == quic::InitialDirection::ClientToServer) {
        ++state.client_initial_packets;
        // Re-run the prior packet-DCID-keyed client accounting on this same
        // tuple, retaining a separate packet-number context per observed DCID.
        auto& baseline = state.dcid_keyed_baseline[packet.destination_connection_id];
        ++baseline.initial_packets;
        const auto baseline_keys = quic::derive_initial_keys(packet.destination_connection_id, true);
        if (!baseline_keys) {
          ++baseline.decrypt_failures;
          ++dcid_keyed_client_decrypt_failures;
        } else {
          const auto baseline_decrypted = quic::decrypt_initial_packet(
              datagram.payload, packet, *baseline_keys.value, baseline.largest_packet_number);
          if (!baseline_decrypted) {
            ++baseline.decrypt_failures;
            ++dcid_keyed_client_decrypt_failures;
          } else {
            ++baseline.decrypted_packets;
            ++dcid_keyed_client_decrypted;
            if (!baseline.largest_packet_number ||
                baseline_decrypted.value->packet_number > *baseline.largest_packet_number) {
              baseline.largest_packet_number = baseline_decrypted.value->packet_number;
            }
          }
        }
      } else {
        ++state.server_initial_packets;
      }
      if (!observation.associated) {
        if (observation.direction == quic::InitialDirection::ClientToServer) {
          ++client_context_misses;
          ++state.client_context_misses;
        } else {
          ++server_context_misses;
          ++state.server_context_misses;
        }
        continue;
      }

      const bool from_client = observation.direction == quic::InitialDirection::ClientToServer;
      const auto keys = quic::derive_initial_keys(observation.original_destination_connection_id,
                                                  from_client);
      if (!keys) {
        if (from_client) {
          ++client_decrypt_failures;
          ++state.client_decrypt_failures;
        } else {
          ++server_decrypt_failures;
          ++state.server_decrypt_failures;
        }
        continue;
      }
      auto& largest_packet_number = from_client ? state.largest_client_packet_number
                                                : state.largest_server_packet_number;
      const auto decrypted = quic::decrypt_initial_packet(datagram.payload, packet, *keys.value,
                                                          largest_packet_number);
      if (!decrypted) {
        if (from_client) {
          ++client_decrypt_failures;
          ++state.client_decrypt_failures;
        } else {
          ++server_decrypt_failures;
          ++state.server_decrypt_failures;
        }
        continue;
      }
      if (from_client) {
        ++client_decrypted_packets;
        ++state.client_decrypted_packets;
      } else {
        ++server_decrypted_packets;
        ++state.server_decrypted_packets;
      }
      if (!largest_packet_number || decrypted.value->packet_number > *largest_packet_number) {
        largest_packet_number = decrypted.value->packet_number;
      }

      if (!from_client) continue;
      const auto frames = quic::parse_initial_frames(decrypted.value->plaintext);
      if (!frames) {
        ++state.frame_parse_failures;
        continue;
      }
      for (const auto& frame : frames.value->crypto_frames) {
        ++state.crypto_frames;
        if (!state.client_crypto.insert(frame.offset, frame.data)) ++state.reassembly_failures;
      }
    }
  }

  std::size_t switched_alias_buckets = 0;
  std::size_t switched_alias_packets = 0;
  std::size_t dcid_keyed_buckets = 0;
  for (const auto& [flow, state] : flows) {
    (void)flow;
    dcid_keyed_buckets += state.dcid_keyed_baseline.size();
  }
  for (const auto& [flow, context] : associations.connections()) {
    (void)flow;
    switched_alias_buckets += context.switched_client_destination_connection_ids.size();
    switched_alias_packets += context.switched_client_initial_packets;
  }
  const std::size_t total_initial_packets = client_initial_packets + server_initial_packets;
  std::cout << "malformed_quic_datagrams=" << malformed_quic_datagrams << "\n"
            << "initial_packets_total=" << total_initial_packets << "\n"
            << "client_initial_packets=" << client_initial_packets << "\n"
            << "server_initial_packets=" << server_initial_packets << "\n"
            << "client_initial_decrypted=" << client_decrypted_packets << "\n"
            << "server_initial_decrypted=" << server_decrypted_packets << "\n"
            << "client_initial_decrypt_failures=" << client_decrypt_failures << "\n"
            << "server_initial_decrypt_failures=" << server_decrypt_failures << "\n"
            << "client_initial_context_misses=" << client_context_misses << "\n"
            << "server_initial_context_misses=" << server_context_misses << "\n"
            << "dcid_keyed_client_initial_packets=" << client_initial_packets << "\n"
            << "dcid_keyed_client_decrypted=" << dcid_keyed_client_decrypted << "\n"
            << "dcid_keyed_client_decrypt_failures=" << dcid_keyed_client_decrypt_failures << "\n"
            << "dcid_keyed_client_dcid_buckets=" << dcid_keyed_buckets << "\n"
            << "switched_dcid_alias_buckets=" << switched_alias_buckets << "\n"
            << "switched_dcid_client_initial_packets=" << switched_alias_packets << "\n"
            << "retry_packets_observed_unsupported=" << retry_packets_observed << "\n"
            << "connections=" << associations.connections().size() << "\n";

  std::size_t complete_count = 0;
  for (const auto& [flow, state] : flows) {
    const auto context_it = associations.connections().find(flow);
    const std::string original_dcid = context_it == associations.connections().end()
        ? "unknown" : (context_it->second.original_destination_connection_id.empty()
                           ? "(empty)" : to_hex(context_it->second.original_destination_connection_id));
    const std::size_t aliases = context_it == associations.connections().end()
        ? 0U : context_it->second.switched_client_destination_connection_ids.size();
    const std::size_t alias_packets = context_it == associations.connections().end()
        ? 0U : context_it->second.switched_client_initial_packets;
    std::size_t legacy_packets = 0;
    std::size_t legacy_decrypted = 0;
    std::size_t legacy_failures = 0;
    for (const auto& [dcid, baseline] : state.dcid_keyed_baseline) {
      (void)dcid;
      legacy_packets += baseline.initial_packets;
      legacy_decrypted += baseline.decrypted_packets;
      legacy_failures += baseline.decrypt_failures;
    }
    std::cout << "connection_flow=" << quic::format_initial_flow(flow)
              << " original_client_initial_dcid=" << original_dcid
              << " dcid_keyed_client_initial_packets=" << legacy_packets
              << " dcid_keyed_client_decrypted_packets=" << legacy_decrypted
              << " dcid_keyed_client_decrypt_failures=" << legacy_failures
              << " dcid_keyed_client_dcid_buckets=" << state.dcid_keyed_baseline.size()
              << " client_initial_packets=" << state.client_initial_packets
              << " server_initial_packets=" << state.server_initial_packets
              << " client_decrypted_packets=" << state.client_decrypted_packets
              << " server_decrypted_packets=" << state.server_decrypted_packets
              << " client_decrypt_failures=" << state.client_decrypt_failures
              << " server_decrypt_failures=" << state.server_decrypt_failures
              << " decrypt_failures=" << (state.client_decrypt_failures + state.server_decrypt_failures)
              << " client_context_misses=" << state.client_context_misses
              << " server_context_misses=" << state.server_context_misses
              << " switched_dcid_alias_buckets=" << aliases
              << " switched_dcid_client_packets=" << alias_packets
              << " frame_parse_failures=" << state.frame_parse_failures
              << " reassembly_failures=" << state.reassembly_failures
              << " crypto_frames=" << state.crypto_frames
              << " contiguous_crypto_bytes=" << state.client_crypto.contiguous_size() << "\n";

    const auto handshake = state.client_crypto.complete_handshake();
    if (!handshake) {
      const auto expected = state.client_crypto.expected_client_hello_size();
      const auto extent = state.client_crypto.observed_extent();
      const auto range_limit = expected.value_or(extent);
      std::cout << "client_hello=incomplete\n"
                << "client_hello_expected_bytes=";
      if (expected) std::cout << *expected;
      else std::cout << "unknown";
      std::cout << "\ncrypto_observed_extent_bytes=" << extent
                << "\ncrypto_missing_ranges_scope="
                << (expected ? "expected_client_hello" : "observed_extent_only")
                << "\ncrypto_missing_ranges="
                << format_ranges(state.client_crypto.missing_ranges(range_limit)) << "\n";
      continue;
    }
    const auto hello = tls::parse_client_hello(*handshake);
    if (!hello) {
      std::cout << "client_hello=parse_error message=" << hello.error->message
                << " offset=" << hello.error->offset << "\n";
      continue;
    }
    ++complete_count;
    std::cout << "client_hello=complete\n"
              << "client_hello_bytes=" << handshake->size() << "\n"
              << "legacy_version=0x" << std::hex << hello.value->legacy_version << std::dec << "\n"
              << "cipher_suite_count=" << hello.value->cipher_suites.size() << "\n"
              << "extension_count=" << hello.value->extension_types.size() << "\n"
              << "supported_group_count=" << hello.value->supported_groups.size() << "\n"
              << "signature_algorithm_count=" << hello.value->signature_algorithms.size() << "\n"
              << "has_sni=" << (hello.value->has_server_name ? "true" : "false") << "\n"
              << "client_hello_hex=";
    print_hex(*handshake);
    std::cout << "\n";
  }
  std::cout << "complete_client_hellos=" << complete_count << "\n";
  return complete_count > 0U ? 0 : 1;
}

void print_usage() {
  std::cerr << "Usage:\n"
            << "  quic-fingerprint --hex <UDP-datagram-hex>\n"
            << "  quic-fingerprint --pcap <classic-Ethernet-PCAP> [--destination-port <port>] "
            << "[--stateful-initial-context]\n"
            << "Stateful Initial context associates server Initial SCIDs with the original client DCID "
            << "on a fixed UDP 4-tuple; Retry and migration are not supported.\n"
            << "PCAP support currently covers Ethernet + unfragmented IPv4/IPv6 UDP; "
            << "PCAPNG and unsupported link/IP headers fail explicitly.\n";
}
} // namespace

int main(int argc, char** argv) {
  if (argc == 3 && std::string_view(argv[1]) == "--hex") {
    auto bytes = from_hex(argv[2]);
    if (!bytes) {
      std::cerr << bytes.error->message << " at " << bytes.error->offset << "\n";
      return 2;
    }
    const auto packets = quic::parse_long_header_datagram(*bytes.value);
    if (!packets) {
      std::cerr << packets.error->message << " at " << packets.error->offset << "\n";
      return 1;
    }
    quic::CryptoReassembly crypto;
    std::optional<std::uint64_t> largest_packet_number;
    bool saw_initial = false;
    for (const auto& packet : *packets.value) {
      std::cout << "packet type=" << quic::packet_type_name(packet.type)
                << " version=" << packet.version
                << " offset=" << packet.packet_start
                << " length=" << (packet.packet_end - packet.packet_start) << "\n";
      if (packet.type != quic::PacketType::Initial) continue;
      saw_initial = true;
      const auto keys = quic::derive_initial_keys(packet.destination_connection_id, true);
      if (!keys) {
        std::cerr << keys.error->message << "\n";
        return 1;
      }
      const auto decrypted = quic::decrypt_initial_packet(*bytes.value, packet, *keys.value,
                                                           largest_packet_number);
      if (!decrypted) {
        std::cerr << "Initial decrypt failed: " << decrypted.error->message << "\n";
        return 1;
      }
      if (!largest_packet_number || decrypted.value->packet_number > *largest_packet_number) {
        largest_packet_number = decrypted.value->packet_number;
      }
      const auto frames = quic::parse_initial_frames(decrypted.value->plaintext);
      if (!frames) {
        std::cerr << "frame parse failed: " << frames.error->message << "\n";
        return 1;
      }
      for (const auto& frame : frames.value->crypto_frames) {
        if (!crypto.insert(frame.offset, frame.data)) {
          std::cerr << "CRYPTO reassembly conflict or bound exceeded\n";
          return 1;
        }
      }
    }
    if (!saw_initial) {
      std::cerr << "No QUIC Initial packet found.\n";
      return 1;
    }
    const auto handshake = crypto.complete_handshake();
    if (!handshake) {
      std::cerr << "Initial packets did not contain a complete contiguous ClientHello (contiguous bytes="
                << crypto.contiguous_size() << ").\n";
      return 1;
    }
    const auto hello = tls::parse_client_hello(*handshake);
    if (!hello) {
      std::cerr << "ClientHello parse failed: " << hello.error->message << "\n";
      return 1;
    }
    std::cout << "client_hello=complete\n"
              << "legacy_version=0x" << std::hex << hello.value->legacy_version << std::dec << "\n"
              << "cipher_suite_count=" << hello.value->cipher_suites.size() << "\n"
              << "extension_count=" << hello.value->extension_types.size() << "\n"
              << "supported_group_count=" << hello.value->supported_groups.size() << "\n"
              << "signature_algorithm_count=" << hello.value->signature_algorithms.size() << "\n"
              << "has_sni=" << (hello.value->has_server_name ? "true" : "false") << "\n"
              << "client_hello_hex=";
    print_hex(*handshake);
    std::cout << "\n";
    return 0;
  }

  if (argc >= 3 && std::string_view(argv[1]) == "--pcap") {
    std::uint16_t port = 443;
    bool stateful_initial_context = false;
    for (int index = 3; index < argc; ++index) {
      const std::string_view option(argv[index]);
      if (option == "--stateful-initial-context") {
        stateful_initial_context = true;
      } else if (option == "--destination-port" && index + 1 < argc) {
        try {
          const unsigned long parsed = std::stoul(argv[++index]);
          if (parsed == 0UL || parsed > 65535UL) throw std::out_of_range("port");
          port = static_cast<std::uint16_t>(parsed);
        } catch (const std::exception&) {
          std::cerr << "invalid destination port\n";
          return 2;
        }
      } else {
        print_usage();
        return 2;
      }
    }
    return stateful_initial_context ? process_pcap_stateful(argv[2], port)
                                    : process_pcap(argv[2], port);
  }

  print_usage();
  return 2;
}
