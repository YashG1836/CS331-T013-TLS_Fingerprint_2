#include "quic/crypto_reassembly.hpp"
#ifdef QUIC_WITH_OPENSSL
#include "quic/initial_crypto.hpp"
#endif
#include "quic/packet_parser.hpp"
#include "tls/client_hello.hpp"
#include <array>
#include <cstdlib>
#include <cstdint>
#include <iostream>
#include <string>

#define CHECK(expr) do { if (!(expr)) { std::cerr << "CHECK failed: " #expr << " at " << __FILE__ << ":" << __LINE__ << "\n"; std::exit(1); } } while (false)
namespace {
#ifdef QUIC_WITH_OPENSSL
quic::Bytes hex(const std::string&s){quic::Bytes b;for(std::size_t i=0;i+1<s.size();i+=2)b.push_back(static_cast<std::uint8_t>(std::stoul(s.substr(i,2),nullptr,16)));return b;}
#endif
void test_varints(){for(const auto&[encoded,value]:std::array<std::pair<quic::Bytes,std::uint64_t>,4>{{{{0x25},37},{{0x7b,0xbd},15293},{{0x9d,0x7f,0x3e,0x7d},494878333},{{0xc2,0x19,0x7c,0x5e,0xff,0x14,0xe8,0x8c},151288809941952652ULL}}}){auto r=quic::decode_varint(encoded,0);CHECK(r&&r.value->value==value&&r.value->encoded_length==encoded.size());}quic::Bytes bad{0x40};CHECK(!quic::decode_varint(bad,0));}
void test_packet_parser(){quic::Bytes d{0xc0,0,0,0,1,1,0xaa,0,0,17};d.insert(d.end(),17,0);auto r=quic::parse_long_header_datagram(d);CHECK(r&&r.value->size()==1);CHECK(r.value->at(0).type==quic::PacketType::Initial);CHECK(r.value->at(0).destination_connection_id==quic::Bytes{0xaa});CHECK(r.value->at(0).packet_end==d.size());auto bad=quic::parse_long_header_datagram(std::span<const std::uint8_t>(d).first(8));CHECK(!bad);}
#ifdef QUIC_WITH_OPENSSL
void test_initial_keys_rfc9001(){auto dcid=hex("8394c8f03e515708");auto keys=quic::derive_initial_keys(dcid,true);CHECK(keys);const auto key=hex("1f369613dd76d5467730efcbe3b1a22d");const auto iv=hex("fa044b2f42a3fd3b46fb255c");const auto hp=hex("9f50449e04a0e810283a1e9933adedd2");CHECK(std::equal(keys.value->key.begin(),keys.value->key.end(),key.begin()));CHECK(std::equal(keys.value->iv.begin(),keys.value->iv.end(),iv.begin()));CHECK(std::equal(keys.value->header_protection_key.begin(),keys.value->header_protection_key.end(),hp.begin()));}
#endif
void test_reassembly(){quic::CryptoReassembly r;const quic::Bytes tail{3,4,5};CHECK(r.insert(2,tail));CHECK(r.contiguous_size()==0);const quic::Bytes head{1,2};CHECK(r.insert(0,head));CHECK(r.contiguous_size()==5);const quic::Bytes same{2,3};CHECK(r.insert(1,same));const quic::Bytes conflict{9};CHECK(!r.insert(1,conflict));}
void test_frame_crypto(){const quic::Bytes plain{0x06,0x00,0x03,0x01,0x02,0x03};auto f=quic::parse_initial_frames(plain);CHECK(f&&f.value->crypto_frames.size()==1);CHECK(f.value->crypto_frames[0].offset==0&&f.value->crypto_frames[0].data.size()==3);}
void test_client_hello(){quic::Bytes hs{1,0,0,50,0x03,0x03};hs.resize(hs.size()+32,0);hs.insert(hs.end(),{0,0,2,0x13,0x01,1,0,0,7,0,43,0,3,2,0x03,0x04});CHECK(hs.size()==54);quic::CryptoReassembly r;CHECK(r.insert(12,std::span<const std::uint8_t>(hs).subspan(12)));CHECK(!r.complete_handshake());CHECK(r.insert(0,std::span<const std::uint8_t>(hs).first(20)));CHECK(r.insert(20,std::span<const std::uint8_t>(hs).subspan(20,hs.size()-20)));auto complete=r.complete_handshake();CHECK(complete);auto parsed=tls::parse_client_hello(*complete);CHECK(parsed);CHECK(parsed.value->cipher_suites.size()==1&&parsed.value->cipher_suites[0]==0x1301);CHECK(parsed.value->supported_versions.size()==1&&parsed.value->supported_versions[0]==0x0304);}
}
int main(){test_varints();test_packet_parser();
#ifdef QUIC_WITH_OPENSSL
 test_initial_keys_rfc9001();
#endif
 test_reassembly();test_frame_crypto();test_client_hello();std::cout<<"all C++ core tests passed\n";}
