#include "quic/initial_crypto.hpp"
#include <openssl/evp.h>
#include <openssl/kdf.h>
#include <algorithm>
#include <array>
#include <limits>
#include <memory>
#include <string>
#include <string_view>

namespace quic {
namespace {
using Ctx = std::unique_ptr<EVP_CIPHER_CTX, decltype(&EVP_CIPHER_CTX_free)>;
Result<Bytes> expand_label(std::span<const std::uint8_t> secret, std::string_view label, std::size_t out_len) {
  constexpr std::string_view prefix = "tls13 ";
  const std::string full = std::string(prefix) + std::string(label);
  if (out_len > 65535 || full.size() > 255) return {std::nullopt, ParseError{"HKDF label is too large", 0}};
  Bytes info{static_cast<std::uint8_t>(out_len >> 8U), static_cast<std::uint8_t>(out_len),
             static_cast<std::uint8_t>(full.size())};
  info.insert(info.end(), full.begin(), full.end()); info.push_back(0); // empty context
  // HKDF-Expand, implemented as the expand-only half of TLS 1.3 HKDF.
  Bytes out(out_len);
  EVP_PKEY_CTX* raw = EVP_PKEY_CTX_new_id(EVP_PKEY_HKDF, nullptr);
  if (!raw) return {std::nullopt, ParseError{"OpenSSL HKDF context allocation failed", 0}};
  std::unique_ptr<EVP_PKEY_CTX, decltype(&EVP_PKEY_CTX_free)> ctx(raw, EVP_PKEY_CTX_free);
  std::size_t n = out.size();
  if (EVP_PKEY_derive_init(ctx.get()) <= 0 || EVP_PKEY_CTX_hkdf_mode(ctx.get(), EVP_PKEY_HKDEF_MODE_EXPAND_ONLY) <= 0 ||
      EVP_PKEY_CTX_set_hkdf_md(ctx.get(), EVP_sha256()) <= 0 ||
      EVP_PKEY_CTX_set1_hkdf_key(ctx.get(), secret.data(), static_cast<int>(secret.size())) <= 0 ||
      EVP_PKEY_CTX_add1_hkdf_info(ctx.get(), info.data(), static_cast<int>(info.size())) <= 0 ||
      EVP_PKEY_derive(ctx.get(), out.data(), &n) <= 0 || n != out_len)
    return {std::nullopt, ParseError{"OpenSSL HKDF-Expand operation failed", 0}};
  return {std::move(out), std::nullopt};
}
Result<Bytes> aes_ecb_block(std::span<const std::uint8_t> key, std::span<const std::uint8_t> block) {
  Ctx ctx(EVP_CIPHER_CTX_new(), EVP_CIPHER_CTX_free);
  if (!ctx || key.size() != 16 || block.size() != 16 || EVP_EncryptInit_ex(ctx.get(), EVP_aes_128_ecb(), nullptr, key.data(), nullptr) != 1 ||
      EVP_CIPHER_CTX_set_padding(ctx.get(), 0) != 1) return {std::nullopt, ParseError{"AES header-protection setup failed", 0}};
  Bytes out(32); int n1=0, n2=0;
  if (EVP_EncryptUpdate(ctx.get(), out.data(), &n1, block.data(), 16) != 1 || EVP_EncryptFinal_ex(ctx.get(), out.data()+n1, &n2) != 1 || n1+n2 != 16)
    return {std::nullopt, ParseError{"AES header-protection operation failed", 0}};
  out.resize(16); return {std::move(out), std::nullopt};
}
std::uint64_t reconstruct_packet_number(std::uint64_t truncated, unsigned bits, std::optional<std::uint64_t> largest) {
  const std::uint64_t window = std::uint64_t{1} << bits;
  const std::uint64_t half = window / 2;
  const std::uint64_t mask = window - 1;
  const std::uint64_t expected = largest ? (*largest + 1) : 0;
  std::uint64_t candidate = (expected & ~mask) | truncated;
  if (candidate + half <= expected && candidate <= ((std::uint64_t{1} << 62U) - window)) candidate += window;
  else if (candidate > expected + half && candidate >= window) candidate -= window;
  return candidate;
}
}
Result<InitialKeys> derive_initial_keys(std::span<const std::uint8_t> dcid, bool from_client) {
  // RFC 9001 §5.2, QUIC v1 initial_salt.
  constexpr std::array<std::uint8_t,20> salt{0x38,0x76,0x2c,0xf7,0xf5,0x59,0x34,0xb3,0x4d,0x17,0x9a,0xe6,0xa4,0xc8,0x0c,0xad,0xcc,0xbb,0x7f,0x0a};
  if (dcid.size() > 20) return {std::nullopt, ParseError{"destination connection ID exceeds 20 bytes", 0}};
  // HKDF-Extract is performed separately from the TLS 1.3 HKDF-Expand-Label steps.
  std::array<std::uint8_t,32> initial_secret{}; std::size_t n=initial_secret.size();
  EVP_PKEY_CTX* raw = EVP_PKEY_CTX_new_id(EVP_PKEY_HKDF, nullptr);
  if (!raw) return {std::nullopt, ParseError{"OpenSSL HKDF context allocation failed", 0}};
  std::unique_ptr<EVP_PKEY_CTX, decltype(&EVP_PKEY_CTX_free)> x(raw, EVP_PKEY_CTX_free);
  if (EVP_PKEY_derive_init(x.get())<=0 || EVP_PKEY_CTX_hkdf_mode(x.get(), EVP_PKEY_HKDEF_MODE_EXTRACT_ONLY)<=0 ||
      EVP_PKEY_CTX_set_hkdf_md(x.get(), EVP_sha256())<=0 || EVP_PKEY_CTX_set1_hkdf_salt(x.get(), salt.data(), static_cast<int>(salt.size()))<=0 ||
      EVP_PKEY_CTX_set1_hkdf_key(x.get(), dcid.data(), static_cast<int>(dcid.size()))<=0 || EVP_PKEY_derive(x.get(), initial_secret.data(), &n)<=0 || n!=32)
    return {std::nullopt, ParseError{"Initial secret derivation failed", 0}};
  auto side = expand_label(initial_secret, from_client ? "client in" : "server in", 32);
  if (!side) return {std::nullopt, side.error};
  auto key = expand_label(*side.value, "quic key", 16); if (!key) return {std::nullopt, key.error};
  auto iv = expand_label(*side.value, "quic iv", 12); if (!iv) return {std::nullopt, iv.error};
  auto hp = expand_label(*side.value, "quic hp", 16); if (!hp) return {std::nullopt, hp.error};
  InitialKeys result;
  std::copy(key.value->begin(), key.value->end(), result.key.begin());
  std::copy(iv.value->begin(), iv.value->end(), result.iv.begin());
  std::copy(hp.value->begin(), hp.value->end(), result.header_protection_key.begin());
  return {result, std::nullopt};
}
Result<DecryptedInitial> decrypt_initial_packet(std::span<const std::uint8_t> datagram, const LongHeaderPacket& p,
                                                const InitialKeys& keys, std::optional<std::uint64_t> largest) {
  if (p.type != PacketType::Initial || p.packet_start >= p.packet_end || p.packet_end > datagram.size() || p.packet_number_offset > p.packet_end)
    return {std::nullopt, ParseError{"invalid Initial packet bounds", p.packet_start}};
  const auto sample_offset = p.packet_number_offset + 4;
  if (sample_offset > p.packet_end || p.packet_end - sample_offset < 16)
    return {std::nullopt, ParseError{"Initial packet is too short for header-protection sample", sample_offset}};
  auto mask = aes_ecb_block(keys.header_protection_key, datagram.subspan(sample_offset,16));
  if (!mask) return {std::nullopt, mask.error};
  Bytes header(datagram.begin()+static_cast<std::ptrdiff_t>(p.packet_start), datagram.begin()+static_cast<std::ptrdiff_t>(p.packet_end));
  const auto pn_rel = p.packet_number_offset-p.packet_start;
  header[0] ^= static_cast<std::uint8_t>((*mask.value)[0] & 0x0fU);
  const unsigned pn_len = static_cast<unsigned>((header[0] & 0x03U)+1U);
  if (pn_rel > header.size() || pn_len > header.size()-pn_rel) return {std::nullopt, ParseError{"truncated packet number", p.packet_number_offset}};
  std::uint64_t truncated=0;
  for (unsigned i=0;i<pn_len;++i) { header[pn_rel+i] ^= (*mask.value)[i+1]; truncated=(truncated<<8U)|header[pn_rel+i]; }
  const auto pn = reconstruct_packet_number(truncated,pn_len*8U,largest);
  const std::size_t aad_len=pn_rel+pn_len;
  if (header.size()<aad_len+16) return {std::nullopt, ParseError{"Initial ciphertext lacks authentication tag", p.packet_number_offset+pn_len}};
  std::array<std::uint8_t,12> nonce=keys.iv;
  for (unsigned i=0;i<8;++i) nonce[11-i] ^= static_cast<std::uint8_t>(pn>>(i*8U));
  const auto ciphertext = std::span<const std::uint8_t>(header).subspan(aad_len);
  const auto cipher_len=ciphertext.size()-16;
  Ctx ctx(EVP_CIPHER_CTX_new(),EVP_CIPHER_CTX_free);
  if (!ctx || EVP_DecryptInit_ex(ctx.get(),EVP_aes_128_gcm(),nullptr,nullptr,nullptr)!=1 ||
      EVP_CIPHER_CTX_ctrl(ctx.get(),EVP_CTRL_GCM_SET_IVLEN,12,nullptr)!=1 || EVP_DecryptInit_ex(ctx.get(),nullptr,nullptr,keys.key.data(),nonce.data())!=1)
    return {std::nullopt, ParseError{"AES-GCM setup failed", p.packet_number_offset}};
  if (aad_len>static_cast<std::size_t>(std::numeric_limits<int>::max())) return {std::nullopt, ParseError{"Initial associated data exceeds OpenSSL size limit", p.packet_start}};
  int n1=0;
  if (EVP_DecryptUpdate(ctx.get(),nullptr,&n1,header.data(),static_cast<int>(aad_len))!=1)
    return {std::nullopt, ParseError{"AES-GCM associated-data processing failed", p.packet_start}};
  Bytes plain(cipher_len+16); int produced=0;
  if (cipher_len>static_cast<std::size_t>(std::numeric_limits<int>::max()) ||
      EVP_DecryptUpdate(ctx.get(),plain.data(),&produced,ciphertext.data(),static_cast<int>(cipher_len))!=1)
    return {std::nullopt, ParseError{"AES-GCM ciphertext processing failed", p.packet_number_offset+pn_len}};
  std::array<std::uint8_t,16>tag{}; std::copy(ciphertext.end()-16,ciphertext.end(),tag.begin());
  if (EVP_CIPHER_CTX_ctrl(ctx.get(),EVP_CTRL_GCM_SET_TAG,16,tag.data())!=1) return {std::nullopt, ParseError{"AES-GCM tag setup failed", p.packet_end-16}};
  int final_n=0;
  if (EVP_DecryptFinal_ex(ctx.get(),plain.data()+produced,&final_n)!=1) return {std::nullopt, ParseError{"Initial packet authentication failed", p.packet_end-16}};
  plain.resize(static_cast<std::size_t>(produced+final_n));
  return {DecryptedInitial{pn,std::move(plain),Bytes(header.begin(),header.begin()+static_cast<std::ptrdiff_t>(aad_len))},std::nullopt};
}
} // namespace quic
