#include "tls/client_hello.hpp"
#include <set>
namespace tls {
namespace {
struct Cursor {
 std::span<const std::uint8_t> b; std::size_t p{};
 bool take8(std::uint8_t& x){if(p>=b.size())return false;x=b[p++];return true;}
 bool take16(std::uint16_t& x){if(b.size()-p<2)return false;x=static_cast<std::uint16_t>((static_cast<unsigned>(b[p])<<8U)|b[p+1]);p+=2;return true;}
 bool take24(std::uint32_t& x){if(b.size()-p<3)return false;x=(static_cast<std::uint32_t>(b[p])<<16U)|(static_cast<std::uint32_t>(b[p+1])<<8U)|b[p+2];p+=3;return true;}
 bool take_bytes(std::size_t n,std::span<const std::uint8_t>& out){if(n>b.size()-p)return false;out=b.subspan(p,n);p+=n;return true;}
};
quic::Result<std::vector<std::uint16_t>> u16_vector(std::span<const std::uint8_t> data, bool length_prefix){
 Cursor c{data}; std::uint16_t n=static_cast<std::uint16_t>(data.size());
 if(length_prefix&&!c.take16(n))return {std::nullopt,quic::ParseError{"truncated TLS vector length",0}};
 if(n!=data.size()-c.p||n%2!=0)return {std::nullopt,quic::ParseError{"invalid TLS uint16 vector length",c.p}};
 std::vector<std::uint16_t> out; while(c.p<data.size()){std::uint16_t v{};c.take16(v);out.push_back(v);}return {std::move(out),std::nullopt};
}
quic::Result<bool> parse_alpn(std::span<const std::uint8_t> b,std::vector<std::string>& out){
 Cursor c{b};std::uint16_t total{};if(!c.take16(total)||total!=b.size()-2)return {std::nullopt,quic::ParseError{"invalid ALPN protocol-name list length",0}};
 while(c.p<b.size()){std::uint8_t n{};if(!c.take8(n)||n==0)return {std::nullopt,quic::ParseError{"invalid ALPN protocol name",c.p}};std::span<const std::uint8_t> name;if(!c.take_bytes(n,name))return {std::nullopt,quic::ParseError{"truncated ALPN protocol name",c.p}};out.emplace_back(name.begin(),name.end());}
 return {true,std::nullopt};
}
}
quic::Result<ClientHello> parse_client_hello(std::span<const std::uint8_t> hs){
 Cursor outer{hs};std::uint8_t type{};std::uint32_t declared{};
 if(!outer.take8(type)||!outer.take24(declared))return {std::nullopt,quic::ParseError{"truncated TLS handshake header",0}};
 if(type!=1)return {std::nullopt,quic::ParseError{"TLS handshake is not ClientHello",0}};
 if(declared!=hs.size()-4)return {std::nullopt,quic::ParseError{"ClientHello handshake length mismatch",1}};
 Cursor c{hs.subspan(4)};ClientHello hello;
 if(!c.take16(hello.legacy_version))return {std::nullopt,quic::ParseError{"truncated ClientHello legacy_version",4}};
 std::span<const std::uint8_t> tmp;
 if(!c.take_bytes(32,tmp))return {std::nullopt,quic::ParseError{"truncated ClientHello random",c.p+4}};
 std::uint8_t len8{};if(!c.take8(len8)||!c.take_bytes(len8,tmp))return {std::nullopt,quic::ParseError{"invalid legacy_session_id",c.p+4}};
 std::uint16_t len16{};if(!c.take16(len16)||len16==0||len16%2||!c.take_bytes(len16,tmp))return {std::nullopt,quic::ParseError{"invalid cipher_suites vector",c.p+4}};
 {Cursor v{tmp};while(v.p<tmp.size()){std::uint16_t x{};v.take16(x);hello.cipher_suites.push_back(x);}}
 if(!c.take8(len8)||len8==0||!c.take_bytes(len8,tmp))return {std::nullopt,quic::ParseError{"invalid legacy_compression_methods",c.p+4}};
 if(!c.take16(len16))return {std::nullopt,quic::ParseError{"missing extensions vector",c.p+4}};
 if(len16!=c.b.size()-c.p)return {std::nullopt,quic::ParseError{"extensions length mismatch",c.p+4}};
 const auto ext_end=c.p+len16;
 std::set<std::uint16_t> seen_extensions;
 while(c.p<ext_end){
   std::uint16_t id{},n{};if(!c.take16(id)||!c.take16(n)||n>ext_end-c.p)return {std::nullopt,quic::ParseError{"truncated TLS extension",c.p+4}};
   if(!seen_extensions.insert(id).second)return {std::nullopt,quic::ParseError{"duplicate ClientHello extension",c.p+4}};
   std::span<const std::uint8_t> data;c.take_bytes(n,data);hello.extension_types.push_back(id);
   if(id==0){ // server_name
     Cursor s{data};std::uint16_t list_len{};if(!s.take16(list_len)||list_len!=data.size()-2)return {std::nullopt,quic::ParseError{"invalid server_name list",c.p+4}};
     while(s.p<data.size()){std::uint8_t nt{};std::uint16_t nl{};if(!s.take8(nt)||!s.take16(nl)||nl>data.size()-s.p)return {std::nullopt,quic::ParseError{"invalid server_name entry",c.p+4}};if(nt==0)hello.has_server_name=true;s.p+=nl;}
   } else if(id==10){auto v=u16_vector(data,true);if(!v)return {std::nullopt,v.error};hello.supported_groups=std::move(*v.value);}
   else if(id==13){auto v=u16_vector(data,true);if(!v)return {std::nullopt,v.error};hello.signature_algorithms=std::move(*v.value);}
   else if(id==43){if(data.empty())return {std::nullopt,quic::ParseError{"empty supported_versions extension",c.p+4}};const auto count=data[0];if(count!=data.size()-1||count%2)return {std::nullopt,quic::ParseError{"invalid supported_versions vector",c.p+4}};auto v=u16_vector(data.subspan(1),false);if(!v)return {std::nullopt,v.error};hello.supported_versions=std::move(*v.value);}
   else if(id==16){auto r=parse_alpn(data,hello.alpn_protocols);if(!r)return {std::nullopt,r.error};}
 }
 return {std::move(hello),std::nullopt};
}
} // namespace tls
