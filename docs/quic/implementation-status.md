# QUIC extraction implementation status

## Supported scope in the current increment

The C++ library supports parsing QUIC v1 long-header packet boundaries from a UDP datagram, deriving client/server Initial traffic secrets from a supplied destination connection ID, removing Initial header protection, authenticating/decrypting an Initial packet, parsing selected Initial frames, reassembling CRYPTO bytes by offset, and validating a TLS ClientHello structure.

The key derivation is checked against the client Initial key/IV/header-protection values in RFC 9001 Appendix A.1. This is a unit-test vector check, not evidence that a captured end-to-end connection succeeds.

The command-line wrapper is deliberately limited to one datagram passed as hexadecimal text. The initial integration path is client-to-server Initial traffic. It is not a pcap parser and does not infer UDP payloads from IP packets. It does not claim support for QUIC v2, Retry, migration, 0-RTT decryption, all QUIC frame types, or JA4 calculation.

## Pipeline and failure behaviour

1. Decode QUIC variable-length integers and parse supported long headers with bounds checks.
2. Derive Initial keys from the packet's destination connection ID, using the v1 salt from RFC 9001 §5.2 and TLS 1.3 HKDF-Expand-Label construction.
3. Apply AES header protection removal before recovering the packet number; authenticate/decrypt with AES-128-GCM.
4. Parse the frame subset required to find Initial CRYPTO bytes. Unknown frame types fail explicitly.
5. Insert CRYPTO ranges at their protocol offsets; equal overlaps are accepted, conflicting overlaps rejected, and a configurable allocation bound prevents attacker-controlled unbounded offsets.
6. Return a handshake only when bytes from offset zero cover the declared ClientHello length. Then validate the TLS ClientHello and selected extension vectors.

## Next engineering gates

- Validate packet decryption against an independently published or generated full-packet vector, including tamper rejection and packet-number reconstruction.
- Complete provenance for the registered provisional QUIC v1 client capture and compare the current modular implementation's recovered ClientHello byte-for-byte with a trusted reference. The archive's monolithic-parser result is not validation of this implementation.
- Add a pcap/UDP extraction adapter without changing the core's bounded-span API.
- Test multiple coalesced packets and CRYPTO fragments across datagrams, including out-of-order delivery and incomplete captures.
- Verify JA4's QUIC protocol identifier and construction against the chosen reference implementation before emitting a JA4 result.
- For each additional capture, register its evidence and provenance in the manifest; make every measured result regenerate from the registered artifacts.
