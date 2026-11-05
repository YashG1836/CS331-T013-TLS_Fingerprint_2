#include "quic/initial_context.hpp"

#include <algorithm>
#include <iomanip>
#include <sstream>
#include <tuple>
#include <utility>

namespace quic {

bool InitialEndpoint::operator<(const InitialEndpoint& other) const {
  return std::tie(ip_version, address, port) <
         std::tie(other.ip_version, other.address, other.port);
}

bool InitialFlowKey::operator<(const InitialFlowKey& other) const {
  return std::tie(client, server) < std::tie(other.client, other.server);
}

namespace {
InitialEndpoint endpoint(std::uint8_t version,
                         const std::array<std::uint8_t, 16>& address,
                         std::uint16_t port) {
  return InitialEndpoint{version, address, port};
}
}  // namespace

InitialAssociationObservation InitialContextAssociator::observe(
    const UdpDatagram& datagram, const LongHeaderPacket& packet,
    std::uint16_t service_port) {
  InitialAssociationObservation observation;
  if (packet.type != PacketType::Initial || packet.version != 1U) return observation;

  InitialFlowKey flow;
  if (datagram.destination_port == service_port &&
      datagram.source_port != service_port) {
    observation.direction = InitialDirection::ClientToServer;
    flow.client = endpoint(datagram.ip_version, datagram.source_address,
                           datagram.source_port);
    flow.server = endpoint(datagram.ip_version, datagram.destination_address,
                           datagram.destination_port);
  } else if (datagram.source_port == service_port &&
             datagram.destination_port != service_port) {
    observation.direction = InitialDirection::ServerToClient;
    flow.client = endpoint(datagram.ip_version, datagram.destination_address,
                           datagram.destination_port);
    flow.server = endpoint(datagram.ip_version, datagram.source_address,
                           datagram.source_port);
  } else {
    return observation;
  }
  observation.flow = flow;

  if (observation.direction == InitialDirection::ClientToServer) {
    auto found = connections_.find(flow);
    if (found == connections_.end()) {
      InitialConnectionContext context;
      context.flow = flow;
      context.original_destination_connection_id = packet.destination_connection_id;
      context.client_source_connection_ids.insert(packet.source_connection_id);
      found = connections_.emplace(flow, std::move(context)).first;
      observation.created_connection = true;
      observation.associated = true;
    } else {
      auto& context = found->second;
      const bool original = packet.destination_connection_id ==
                            context.original_destination_connection_id;
      const bool server_alias = context.server_source_connection_ids.contains(
          packet.destination_connection_id);
      if (!original && !server_alias) {
        observation.original_destination_connection_id =
            context.original_destination_connection_id;
        return observation;  // Unknown CID: do not silently replace the key context.
      }
      observation.used_switched_dcid = server_alias && !original;
      if (observation.used_switched_dcid) {
        context.switched_client_destination_connection_ids.insert(
            packet.destination_connection_id);
        ++context.switched_client_initial_packets;
      }
      context.client_source_connection_ids.insert(packet.source_connection_id);
      observation.associated = true;
    }
    observation.original_destination_connection_id =
        found->second.original_destination_connection_id;
    return observation;
  }

  const auto found = connections_.find(flow);
  if (found == connections_.end()) return observation;
  auto& context = found->second;
  // A server Initial's DCID must identify a client source CID observed on this
  // tuple. In the supplied traces that CID is empty; empty CIDs are valid set
  // members and are intentionally retained.
  if (!context.client_source_connection_ids.contains(
          packet.destination_connection_id)) {
    observation.original_destination_connection_id =
        context.original_destination_connection_id;
    return observation;
  }
  if (!packet.source_connection_id.empty()) {
    context.server_source_connection_ids.insert(packet.source_connection_id);
  }
  observation.associated = true;
  observation.original_destination_connection_id =
      context.original_destination_connection_id;
  return observation;
}

std::string format_initial_endpoint(const InitialEndpoint& endpoint_value) {
  std::ostringstream out;
  if (endpoint_value.ip_version == 4U) {
    for (std::size_t i = 12U; i < 16U; ++i) {
      if (i != 12U) out << '.';
      out << std::dec << static_cast<unsigned>(endpoint_value.address[i]);
    }
  } else {
    out << '[';
    for (std::size_t i = 0; i < 16U; ++i) {
      if (i != 0U && (i % 2U) == 0U) out << ':';
      out << std::hex << std::setw(2) << std::setfill('0')
          << static_cast<unsigned>(endpoint_value.address[i]);
    }
    out << ']';
  }
  out << ':' << std::dec << endpoint_value.port;
  return out.str();
}

std::string format_initial_flow(const InitialFlowKey& flow) {
  return format_initial_endpoint(flow.client) + "->" +
         format_initial_endpoint(flow.server);
}

const char* initial_direction_name(InitialDirection direction) {
  switch (direction) {
    case InitialDirection::ClientToServer: return "client-to-server";
    case InitialDirection::ServerToClient: return "server-to-client";
    default: return "unknown";
  }
}

}  // namespace quic
