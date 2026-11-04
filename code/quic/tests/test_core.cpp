#include "quic/capture_reader.hpp"
#include "quic/crypto_reassembly.hpp"
#include "quic/frame_parser.hpp"
#include "quic/initial_crypto.hpp"
#include "quic/packet_parser.hpp"
#include "tls/client_hello.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

#define CHECK(expr)                                                                  \
  do {                                                                               \
    if (!(expr)) {                                                                   \
      std::cerr << "CHECK failed: " #expr " at " << __FILE__ << ":" << __LINE__   \
                << "\n";                                                            \
      std::exit(1);                                                                  \
    }                                                                                \
  } while (false)

namespace {

quic::Bytes hex(std::string_view text) {
  const auto nibble = [](char ch) -> int {
    if (ch >= '0' && ch <= '9') return ch - '0';
    if (ch >= 'a' && ch <= 'f') return ch - 'a' + 10;
    if (ch >= 'A' && ch <= 'F') return ch - 'A' + 10;
    return -1;
  };

  quic::Bytes bytes;
  int high = -1;
  for (const char ch : text) {
    if (std::isspace(static_cast<unsigned char>(ch))) continue;
    const int value = nibble(ch);
    CHECK(value >= 0);
    if (high < 0) {
      high = value;
    } else {
      bytes.push_back(static_cast<std::uint8_t>((high << 4) | value));
      high = -1;
    }
  }
  CHECK(high < 0);
  return bytes;
}

void test_varints() {
  const std::array<std::pair<quic::Bytes, std::uint64_t>, 4> examples{{
      {{0x25}, 37},
      {{0x7b, 0xbd}, 15293},
      {{0x9d, 0x7f, 0x3e, 0x7d}, 494878333},
      {{0xc2, 0x19, 0x7c, 0x5e, 0xff, 0x14, 0xe8, 0x8c}, 151288809941952652ULL},
  }};
  for (const auto& [encoded, value] : examples) {
    const auto result = quic::decode_varint(encoded, 0);
    CHECK(result);
    CHECK(result.value->value == value);
    CHECK(result.value->encoded_length == encoded.size());
  }

  const quic::Bytes truncated{0x40};
  CHECK(!quic::decode_varint(truncated, 0));
  CHECK(!quic::decode_varint(quic::Bytes{}, 0));
}

void test_packet_parser() {
  quic::Bytes datagram{0xc0, 0, 0, 0, 1, 1, 0xaa, 0, 0, 17};
  datagram.insert(datagram.end(), 17, 0);
  const auto parsed = quic::parse_long_header_datagram(datagram);
  CHECK(parsed);
  CHECK(parsed.value->size() == 1);
  CHECK(parsed.value->at(0).type == quic::PacketType::Initial);
  CHECK(parsed.value->at(0).destination_connection_id == quic::Bytes{0xaa});
  CHECK(parsed.value->at(0).packet_end == datagram.size());

  const auto truncated = quic::parse_long_header_datagram(
      std::span<const std::uint8_t>(datagram).first(8));
  CHECK(!truncated);

  quic::Bytes coalesced = datagram;
  quic::Bytes handshake{0xe0, 0, 0, 0, 1, 0, 0, 17};
  handshake.insert(handshake.end(), 17, 0);
  coalesced.insert(coalesced.end(), handshake.begin(), handshake.end());
  const auto parsed_coalesced = quic::parse_long_header_datagram(coalesced);
  CHECK(parsed_coalesced);
  CHECK(parsed_coalesced.value->size() == 2);
  CHECK(parsed_coalesced.value->at(1).type == quic::PacketType::Handshake);
  CHECK(parsed_coalesced.value->at(1).packet_start == datagram.size());
}

void test_initial_keys_rfc9001() {
  const auto dcid = hex("8394c8f03e515708");
  const auto client = quic::derive_initial_keys(dcid, true);
  CHECK(client);
  CHECK(std::equal(client.value->key.begin(), client.value->key.end(),
                   hex("1f369613dd76d5467730efcbe3b1a22d").begin()));
  CHECK(std::equal(client.value->iv.begin(), client.value->iv.end(),
                   hex("fa044b2f42a3fd3b46fb255c").begin()));
  CHECK(std::equal(client.value->header_protection_key.begin(),
                   client.value->header_protection_key.end(),
                   hex("9f50449e04a0e810283a1e9933adedd2").begin()));

  const auto server = quic::derive_initial_keys(dcid, false);
  CHECK(server);
  CHECK(std::equal(server.value->key.begin(), server.value->key.end(),
                   hex("cf3a5331653c364c88f0f379b6067e37").begin()));
  CHECK(std::equal(server.value->iv.begin(), server.value->iv.end(),
                   hex("0ac1493ca1905853b0bba03e").begin()));
  CHECK(std::equal(server.value->header_protection_key.begin(),
                   server.value->header_protection_key.end(),
                   hex("c206b8d9b9f0f37644430b490eeaa314").begin()));

  CHECK(!quic::derive_initial_keys(hex("000102030405060708090a0b0c0d0e0f1011121314"), true));
}

void test_initial_decryption_rfc9001() {
  // RFC 9001 Appendix A.2, protected client Initial packet. The corresponding
  // packet number is 2, and the packet contains a complete ClientHello CRYPTO
  // frame followed by PADDING.
  const auto packet_bytes = hex(R"HEX(
    c000000001088394c8f03e5157080000 449e7b9aec34d1b1c98dd7689fb8ec11
    d242b123dc9bd8bab936b47d92ec356c 0bab7df5976d27cd449f63300099f399
    1c260ec4c60d17b31f8429157bb35a12 82a643a8d2262cad67500cadb8e7378c
    8eb7539ec4d4905fed1bee1fc8aafba1 7c750e2c7ace01e6005f80fcb7df6212
    30c83711b39343fa028cea7f7fb5ff89 eac2308249a02252155e2347b63d58c5
    457afd84d05dfffdb20392844ae81215 4682e9cf012f9021a6f0be17ddd0c208
    4dce25ff9b06cde535d0f920a2db1bf3 62c23e596d11a4f5a6cf3948838a3aec
    4e15daf8500a6ef69ec4e3feb6b1d98e 610ac8b7ec3faf6ad760b7bad1db4ba3
    485e8a94dc250ae3fdb41ed15fb6a8e5 eba0fc3dd60bc8e30c5c4287e53805db
    059ae0648db2f64264ed5e39be2e20d8 2df566da8dd5998ccabdae053060ae6c
    7b4378e846d29f37ed7b4ea9ec5d82e7 961b7f25a9323851f681d582363aa5f8
    9937f5a67258bf63ad6f1a0b1d96dbd4 faddfcefc5266ba6611722395c906556
    be52afe3f565636ad1b17d508b73d874 3eeb524be22b3dcbc2c7468d54119c74
    68449a13d8e3b95811a198f3491de3e7 fe942b330407abf82a4ed7c1b311663a
    c69890f4157015853d91e923037c227a 33cdd5ec281ca3f79c44546b9d90ca00
    f064c99e3dd97911d39fe9c5d0b23a22 9a234cb36186c4819e8b9c5927726632
    291d6a418211cc2962e20fe47feb3edf 330f2c603a9d48c0fcb5699dbfe58964
    25c5bac4aee82e57a85aaf4e2513e4f0 5796b07ba2ee47d80506f8d2c25e50fd
    14de71e6c418559302f939b0e1abd576 f279c4b2e0feb85c1f28ff18f58891ff
    ef132eef2fa09346aee33c28eb130ff2 8f5b766953334113211996d20011a198
    e3fc433f9f2541010ae17c1bf202580f 6047472fb36857fe843b19f5984009dd
    c324044e847a4f4a0ab34f719595de37 252d6235365e9b84392b061085349d73
    203a4a13e96f5432ec0fd4a1ee65accd d5e3904df54c1da510b0ff20dcc0c77f
    cb2c0e0eb605cb0504db87632cf3d8b4 dae6e705769d1de354270123cb11450e
    fc60ac47683d7b8d0f811365565fd98c 4c8eb936bcab8d069fc33bd801b03ade
    a2e1fbc5aa463d08ca19896d2bf59a07 1b851e6c239052172f296bfb5e724047
    90a2181014f3b94a4e97d117b4381303 68cc39dbb2d198065ae3986547926cd2
    162f40a29f0c3c8745c0f50fba3852e5 66d44575c29d39a03f0cda721984b6f4
    40591f355e12d439ff150aab7613499d bd49adabc8676eef023b15b65bfc5ca0
    6948109f23f350db82123535eb8a7433 bdabcb909271a6ecbcb58b936a88cd4e
    8f2e6ff5800175f113253d8fa9ca8885 c2f552e657dc603f252e1a8e308f76f0
    be79e2fb8f5d5fbbe2e30ecadd220723 c8c0aea8078cdfcb3868263ff8f09400
    54da48781893a7e49ad5aff4af300cd8 04a6b6279ab3ff3afb64491c85194aab
    760d58a606654f9f4400e8b38591356f bf6425aca26dc85244259ff2b19c41b9
    f96f3ca9ec1dde434da7d2d392b905dd f3d1f9af93d1af5950bd493f5aa731b4
    056df31bd267b6b90a079831aaf579be 0a39013137aac6d404f518cfd4684064
    7e78bfe706ca4cf5e9c5453e9f7cfd2b 8b4c8d169a44e55c88d4a9a7f9474241
    e221af44860018ab0856972e194cd934
  )HEX");

  const auto packets = quic::parse_long_header_datagram(packet_bytes);
  CHECK(packets);
  CHECK(packets.value->size() == 1);
  const auto& packet = packets.value->front();
  CHECK(packet.type == quic::PacketType::Initial);
  CHECK(packet.destination_connection_id == hex("8394c8f03e515708"));

  const auto keys = quic::derive_initial_keys(packet.destination_connection_id, true);
  CHECK(keys);
  const auto decrypted = quic::decrypt_initial_packet(packet_bytes, packet, *keys.value);
  CHECK(decrypted);
  CHECK(decrypted.value->packet_number == 2);
  CHECK(decrypted.value->plaintext.size() == 1162);

  const auto frames = quic::parse_initial_frames(decrypted.value->plaintext);
  CHECK(frames);
  CHECK(frames.value->crypto_frames.size() == 1);
  CHECK(frames.value->crypto_frames.front().offset == 0);
  CHECK(frames.value->crypto_frames.front().data.size() == 241);

  quic::CryptoReassembly reassembly;
  CHECK(reassembly.insert(frames.value->crypto_frames.front().offset,
                          frames.value->crypto_frames.front().data));
  const auto handshake = reassembly.complete_handshake();
  CHECK(handshake);
  const auto hello = tls::parse_client_hello(*handshake);
  CHECK(hello);
  CHECK(!hello.value->cipher_suites.empty());
  CHECK(hello.value->has_server_name);

  auto tampered = packet_bytes;
  tampered.back() ^= 0x01;
  const auto rejected = quic::decrypt_initial_packet(tampered, packet, *keys.value);
  CHECK(!rejected);
}

void test_reassembly() {
  quic::CryptoReassembly reassembly(8);
  const quic::Bytes tail{3, 4, 5};
  CHECK(reassembly.insert(2, tail));
  CHECK(reassembly.contiguous_size() == 0);
  const quic::Bytes head{1, 2};
  CHECK(reassembly.insert(0, head));
  CHECK(reassembly.contiguous_size() == 5);
  const quic::Bytes identical_overlap{2, 3};
  CHECK(reassembly.insert(1, identical_overlap));
  const quic::Bytes conflicting_overlap{9};
  CHECK(!reassembly.insert(1, conflicting_overlap));
  CHECK(!reassembly.insert(1024, quic::Bytes{1}));

  quic::CryptoReassembly damaged(32);
  const quic::Bytes prefix{1, 0, 0, 8, 10, 11}; // ClientHello handshake length is 12 bytes total.
  const quic::Bytes suffix{20, 21, 22};
  CHECK(damaged.insert(0, prefix));
  CHECK(damaged.insert(8, suffix));
  CHECK(damaged.expected_client_hello_size() == 12U);
  CHECK(damaged.observed_extent() == 11U);
  const std::vector<std::pair<std::uint64_t, std::uint64_t>> expected_gaps{{6U, 8U}, {11U, 12U}};
  CHECK(damaged.missing_ranges(12U) == expected_gaps);
}

void test_frame_parser() {
  const quic::Bytes plaintext{0x06, 0x00, 0x03, 0x01, 0x02, 0x03};
  const auto frames = quic::parse_initial_frames(plaintext);
  CHECK(frames);
  CHECK(frames.value->crypto_frames.size() == 1);
  CHECK(frames.value->crypto_frames[0].offset == 0);
  CHECK(frames.value->crypto_frames[0].data == quic::Bytes({1, 2, 3}));

  const quic::Bytes truncated_crypto{0x06, 0x00, 0x04, 0x01, 0x02};
  CHECK(!quic::parse_initial_frames(truncated_crypto));
  const quic::Bytes unsupported{0x04};
  CHECK(!quic::parse_initial_frames(unsupported));
}

void test_client_hello() {
  quic::Bytes handshake{1, 0, 0, 50, 0x03, 0x03};
  handshake.resize(handshake.size() + 32, 0);
  handshake.insert(handshake.end(), {0, 0, 2, 0x13, 0x01, 1, 0, 0, 7, 0, 43, 0, 3, 2,
                                     0x03, 0x04});
  CHECK(handshake.size() == 54);

  quic::CryptoReassembly reassembly;
  CHECK(reassembly.insert(12, std::span<const std::uint8_t>(handshake).subspan(12)));
  CHECK(!reassembly.complete_handshake());
  CHECK(reassembly.insert(0, std::span<const std::uint8_t>(handshake).first(20)));
  CHECK(reassembly.insert(20, std::span<const std::uint8_t>(handshake).subspan(20)));
  const auto complete = reassembly.complete_handshake();
  CHECK(complete);
  const auto parsed = tls::parse_client_hello(*complete);
  CHECK(parsed);
  CHECK(parsed.value->cipher_suites.size() == 1);
  CHECK(parsed.value->cipher_suites[0] == 0x1301);
  CHECK(parsed.value->supported_versions.size() == 1);
  CHECK(parsed.value->supported_versions[0] == 0x0304);

  auto malformed = *complete;
  malformed[3]--;
  CHECK(!tls::parse_client_hello(malformed));
}

void append_le16(quic::Bytes& bytes, std::uint16_t value) {
  bytes.push_back(static_cast<std::uint8_t>(value & 0xffU));
  bytes.push_back(static_cast<std::uint8_t>(value >> 8U));
}

void append_be16(quic::Bytes& bytes, std::uint16_t value) {
  bytes.push_back(static_cast<std::uint8_t>(value >> 8U));
  bytes.push_back(static_cast<std::uint8_t>(value & 0xffU));
}

void append_le32(quic::Bytes& bytes, std::uint32_t value) {
  for (unsigned int shift = 0; shift < 32U; shift += 8U) {
    bytes.push_back(static_cast<std::uint8_t>((value >> shift) & 0xffU));
  }
}

void test_classic_pcap_udp_reader() {
  const quic::Bytes udp_payload{0xc0, 0x00, 0x00, 0x00, 0x01};
  quic::Bytes frame(12U, 0);
  frame.push_back(0x08); // Ethernet IPv4
  frame.push_back(0x00);
  frame.push_back(0x45); // IPv4, 20-byte header
  frame.push_back(0x00);
  const auto ip_total = static_cast<std::uint16_t>(20U + 8U + udp_payload.size());
  append_be16(frame, ip_total);
  frame.push_back(0x00); frame.push_back(0x01); // ID
  frame.push_back(0x40); frame.push_back(0x00); // DF, no fragmentation
  frame.push_back(64); frame.push_back(17); // TTL, UDP
  frame.push_back(0); frame.push_back(0); // checksum
  frame.insert(frame.end(), {192, 0, 2, 1, 198, 51, 100, 2});
  append_be16(frame, 12345); append_be16(frame, 443);
  const auto udp_length = static_cast<std::uint16_t>(8U + udp_payload.size());
  frame.push_back(static_cast<std::uint8_t>(udp_length >> 8U));
  frame.push_back(static_cast<std::uint8_t>(udp_length & 0xffU));
  frame.push_back(0); frame.push_back(0); // checksum
  frame.insert(frame.end(), udp_payload.begin(), udp_payload.end());

  quic::Bytes pcap{0xd4, 0xc3, 0xb2, 0xa1}; // little-endian classic PCAP
  append_le16(pcap, 2); append_le16(pcap, 4);
  append_le32(pcap, 0); append_le32(pcap, 0);
  append_le32(pcap, 65535); append_le32(pcap, 1); // snaplen, Ethernet
  append_le32(pcap, 1); append_le32(pcap, 0);
  append_le32(pcap, static_cast<std::uint32_t>(frame.size()));
  append_le32(pcap, static_cast<std::uint32_t>(frame.size()));
  pcap.insert(pcap.end(), frame.begin(), frame.end());

  const auto path = std::filesystem::temp_directory_path() / "quic_capture_reader_test.pcap";
  {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    CHECK(out.good());
    out.write(reinterpret_cast<const char*>(pcap.data()), static_cast<std::streamsize>(pcap.size()));
    CHECK(out.good());
  }
  const auto parsed = quic::read_ethernet_udp_pcap(path);
  CHECK(parsed);
  CHECK(parsed.value->version_major == 2);
  CHECK(parsed.value->version_minor == 4);
  CHECK(parsed.value->link_type == 1);
  CHECK(parsed.value->packet_records == 1);
  CHECK(parsed.value->udp_datagrams.size() == 1);
  CHECK(parsed.value->udp_datagrams[0].frame_number == 1);
  CHECK(parsed.value->udp_datagrams[0].ip_version == 4);
  CHECK(parsed.value->udp_datagrams[0].source_port == 12345);
  CHECK(parsed.value->udp_datagrams[0].destination_port == 443);
  CHECK(parsed.value->udp_datagrams[0].payload == udp_payload);
  std::filesystem::remove(path);

  const auto invalid_path = std::filesystem::temp_directory_path() / "quic_capture_reader_invalid.pcapng";
  {
    const std::array<std::uint8_t, 4> pcapng_magic{0x0a, 0x0d, 0x0d, 0x0a};
    std::ofstream out(invalid_path, std::ios::binary | std::ios::trunc);
    out.write(reinterpret_cast<const char*>(pcapng_magic.data()),
              static_cast<std::streamsize>(pcapng_magic.size()));
  }
  CHECK(!quic::read_ethernet_udp_pcap(invalid_path));
  std::filesystem::remove(invalid_path);
}

}  // namespace

int main() {
  test_varints();
  test_packet_parser();
  test_classic_pcap_udp_reader();
  test_initial_keys_rfc9001();
  test_initial_decryption_rfc9001();
  test_reassembly();
  test_frame_parser();
  test_client_hello();
  std::cout << "all C++ core tests passed\n";
}
