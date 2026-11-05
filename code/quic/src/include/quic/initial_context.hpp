#pragma once

#include "quic/capture_reader.hpp"

#include <array>
#include <cstdint>
#include <map>
#include <optional>
#include <set>
#include <string>

namespace quic {

struct InitialEndpoint {
  std::uint8_t ip_version{};
  std::array<std::uint8_t, 16> address{};
  std::uint16_t port{};

  bool operator<(const InitialEndpoint& other) const;
};

// A stable, direction-normalized 4-tuple: client endpoint first, server second.
struct InitialFlowKey {
  InitialEndpoint client;
  InitialEndpoint server;

  bool operator<(const InitialFlowKey& other) const;
};

enum class InitialDirection { ClientToServer, ServerToClient, Unknown };

struct InitialConnectionContext {
  InitialFlowKey flow;
  Bytes original_destination_connection_id;
  std::set<Bytes> client_source_connection_ids;
  std::set<Bytes> server_source_connection_ids;
  std::set<Bytes> switched_client_destination_connection_ids;
  std::size_t switched_client_initial_packets{};
};

struct InitialAssociationObservation {
  std::optional<InitialFlowKey> flow;
  InitialDirection direction{InitialDirection::Unknown};
  bool associated{};
  bool created_connection{};
  bool used_switched_dcid{};
  Bytes original_destination_connection_id;
};

// Associates QUIC v1 Initial packets on one UDP 4-tuple with the original
// client Initial DCID. Server Initial SCIDs are remembered as aliases so a
// later client Initial using that CID can still use the original key context.
// This deliberately does not infer across tuple changes/migration or process
// Retry; those require additional validated connection state.
class InitialContextAssociator {
 public:
  InitialAssociationObservation observe(const UdpDatagram& datagram,
                                        const LongHeaderPacket& packet,
                                        std::uint16_t service_port);

  const std::map<InitialFlowKey, InitialConnectionContext>& connections() const {
    return connections_;
  }

 private:
  std::map<InitialFlowKey, InitialConnectionContext> connections_;
};

std::string format_initial_endpoint(const InitialEndpoint& endpoint);
std::string format_initial_flow(const InitialFlowKey& flow);
const char* initial_direction_name(InitialDirection direction);

}  // namespace quic
