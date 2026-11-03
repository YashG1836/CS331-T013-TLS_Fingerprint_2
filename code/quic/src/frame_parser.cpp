#include "quic/frame_parser.hpp"
#include <limits>
namespace quic {
namespace {
Result<std::uint64_t> take(std::span<const std::uint8_t> b,std::size_t& p) { auto r=decode_varint(b,p); if(!r)return {std::nullopt,r.error}; p+=r.value->encoded_length; return {r.value->value,std::nullopt}; }
bool skip_bytes(std::span<const std::uint8_t> b,std::size_t& p,std::uint64_t n) { if(n>b.size()-p)return false; p+=static_cast<std::size_t>(n); return true; }
}
Result<FrameParseResult> parse_initial_frames(std::span<const std::uint8_t> b) {
  FrameParseResult out; std::size_t p=0;
  while(p<b.size()) {
    const auto frame_at=p;
    if(b[p]==0){ while(p<b.size()&&b[p]==0)++p; ++out.frames_seen; continue; }
    auto type=take(b,p); if(!type)return {std::nullopt,type.error}; ++out.frames_seen;
    switch(*type.value) {
      case 1: // PING
        break;
      case 2: case 3: { // ACK / ACK_ECN
        auto largest=take(b,p); if(!largest)return {std::nullopt,largest.error};
        auto delay=take(b,p); if(!delay)return {std::nullopt,delay.error};
        auto ranges=take(b,p); if(!ranges)return {std::nullopt,ranges.error};
        auto first_range=take(b,p); if(!first_range)return {std::nullopt,first_range.error};
        if(*ranges.value>100000) return {std::nullopt,ParseError{"ACK range count exceeds safety limit",frame_at}};
        for(std::uint64_t i=0;i<*ranges.value;++i){auto gap=take(b,p);if(!gap)return {std::nullopt,gap.error};auto range=take(b,p);if(!range)return {std::nullopt,range.error};}
        if(*type.value==3) for(int i=0;i<3;++i){auto count=take(b,p);if(!count)return {std::nullopt,count.error};}
        break;
      }
      case 6: { // CRYPTO
        auto offset=take(b,p);if(!offset)return {std::nullopt,offset.error};
        auto len=take(b,p);if(!len)return {std::nullopt,len.error};
        if(*len.value>b.size()-p)return {std::nullopt,ParseError{"truncated CRYPTO frame data",p}};
        const auto end=p+static_cast<std::size_t>(*len.value);
        out.crypto_frames.push_back(CryptoFrame{*offset.value,Bytes(b.begin()+static_cast<std::ptrdiff_t>(p),b.begin()+static_cast<std::ptrdiff_t>(end))}); p=end;
        break;
      }
      case 0x1c: { // transport CONNECTION_CLOSE
        for(int i=0;i<3;++i){auto f=take(b,p);if(!f)return {std::nullopt,f.error};}
        auto len=take(b,p);if(!len)return {std::nullopt,len.error};
        if(!skip_bytes(b,p,*len.value))return {std::nullopt,ParseError{"truncated CONNECTION_CLOSE reason",p}};
        break;
      }
      case 0x1d: { // application CONNECTION_CLOSE
        auto code=take(b,p);if(!code)return {std::nullopt,code.error};
        auto len=take(b,p);if(!len)return {std::nullopt,len.error};
        if(!skip_bytes(b,p,*len.value))return {std::nullopt,ParseError{"truncated CONNECTION_CLOSE reason",p}};
        break;
      }
      default:
        return {std::nullopt,ParseError{"unsupported frame type in Initial packet: " + std::to_string(*type.value),frame_at}};
    }
  }
  return {std::move(out),std::nullopt};
}
} // namespace quic
