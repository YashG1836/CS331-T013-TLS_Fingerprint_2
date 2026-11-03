#include "quic/crypto_reassembly.hpp"
#include "quic/initial_crypto.hpp"
#include "quic/packet_parser.hpp"
#include "tls/client_hello.hpp"
#include <cctype>
#include <iostream>
#include <optional>
#include <string>

namespace {
quic::Result<quic::Bytes> from_hex(const std::string& s){
  quic::Bytes out; int high=-1;
  for(std::size_t i=0;i<s.size();++i){const unsigned char c=static_cast<unsigned char>(s[i]);if(std::isspace(c))continue;int v=-1;if(c>='0'&&c<='9')v=c-'0';else if(c>='a'&&c<='f')v=c-'a'+10;else if(c>='A'&&c<='F')v=c-'A'+10;else return {std::nullopt,quic::ParseError{"input contains a non-hex character",i}};if(high<0)high=v;else{out.push_back(static_cast<std::uint8_t>((high<<4)|v));high=-1;}}
  if(high>=0)return {std::nullopt,quic::ParseError{"hex input has an odd number of digits",s.size()}};return {std::move(out),std::nullopt};
}
void print_hex(const quic::Bytes& b){static constexpr char digits[]="0123456789abcdef";for(auto x:b)std::cout<<digits[x>>4U]<<digits[x&15U];}
}
int main(int argc,char**argv){
  if(argc!=3||std::string(argv[1])!="--hex") {std::cerr<<"Usage: quic-fingerprint --hex <UDP-datagram-hex>\nThis first-stage CLI accepts one QUIC v1 datagram (spaces in hex are allowed).\n";return 2;}
  auto bytes=from_hex(argv[2]);if(!bytes){std::cerr<<bytes.error->message<<" at "<<bytes.error->offset<<"\n";return 2;}
  auto packets=quic::parse_long_header_datagram(*bytes.value);if(!packets){std::cerr<<packets.error->message<<" at "<<packets.error->offset<<"\n";return 1;}
  quic::CryptoReassembly crypto;
  std::optional<std::uint64_t> largest_packet_number;
  bool saw_initial=false;
  for(const auto& packet:*packets.value){
    std::cout<<"packet type="<<quic::packet_type_name(packet.type)<<" version="<<packet.version<<" offset="<<packet.packet_start<<" length="<<(packet.packet_end-packet.packet_start)<<"\n";
    if(packet.type!=quic::PacketType::Initial)continue;
    saw_initial=true;
    auto keys=quic::derive_initial_keys(packet.destination_connection_id,true);
    if(!keys){std::cerr<<keys.error->message<<"\n";return 1;}
    auto clear=quic::decrypt_initial_packet(*bytes.value,packet,*keys.value,largest_packet_number);
    if(!clear){std::cerr<<"Initial decrypt failed: "<<clear.error->message<<"\n";return 1;}
    std::cout<<"decrypted client Initial packet_number="<<clear.value->packet_number<<"\n";
    if(!largest_packet_number||clear.value->packet_number>*largest_packet_number)largest_packet_number=clear.value->packet_number;
    auto frames=quic::parse_initial_frames(clear.value->plaintext);
    if(!frames){std::cerr<<"frame parse failed: "<<frames.error->message<<"\n";return 1;}
    for(const auto& frame:frames.value->crypto_frames){auto inserted=crypto.insert(frame.offset,frame.data);if(!inserted){std::cerr<<inserted.error->message<<"\n";return 1;}}
  }
  if(!saw_initial){std::cerr<<"No QUIC v1 Initial packet found.\n";return 1;}
  auto handshake=crypto.complete_handshake();if(!handshake){std::cerr<<"Initial packets did not contain a complete contiguous ClientHello (contiguous bytes="<<crypto.contiguous_size()<<").\n";return 1;}
  auto hello=tls::parse_client_hello(*handshake);if(!hello){std::cerr<<"ClientHello parse failed: "<<hello.error->message<<"\n";return 1;}
  std::cout<<"client_hello=complete\nlegacy_version=0x"<<std::hex<<hello.value->legacy_version<<std::dec<<"\ncipher_suite_count="<<hello.value->cipher_suites.size()<<"\nextension_count="<<hello.value->extension_types.size()<<"\nsupported_group_count="<<hello.value->supported_groups.size()<<"\nsignature_algorithm_count="<<hello.value->signature_algorithms.size()<<"\nhas_sni="<<(hello.value->has_server_name?"true":"false")<<"\nclient_hello_hex=";print_hex(*handshake);std::cout<<"\n";
  std::cout<<"JA4 is intentionally not emitted yet: its QUIC protocol encoding must first be validated against the chosen reference implementation.\n";
  return 0;
}
