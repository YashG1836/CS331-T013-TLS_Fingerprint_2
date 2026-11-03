# QUIC extraction implementation status

## Supported scope in the current increment

The C++ library supports QUIC v1 long-header packet-boundary parsing from UDP datagrams, client/server Initial secret derivation from a supplied destination connection ID, Initial header-protection removal, AES-128-GCM authentication/decryption, selected Initial frame parsing, offset-aware CRYPTO reassembly, and TLS ClientHello validation.

The key derivation is checked against the client Initial key/IV/header-protection values in RFC 9001 Appendix A.1. This unit vector is separate from end-to-end capture evidence.

The current CLI accepts a UDP datagram as hex or a classic-PCAP v2.x Ethernet capture. PCAP mode extracts UDP from unfragmented IPv4/IPv6, filters destination port 443 by default, parses QUIC v1 client Initial packets, and retains CRYPTO reassembly state by DCID. It does not yet provide a complete bidirectional connection model or handle PCAPNG, VLAN tags, IP fragments, IPv6 extension chains, QUIC v2, Retry, migration, 0-RTT decryption, all frame types, or JA4 calculation.

The user reports a direct Ubuntu WSL run in which the CLI recovered five ClientHellos from each imported QUIC capture and all ten byte strings matched TShark 4.6.4 `tls.handshake_raw` outputs by unordered set comparison. The WSL raw exports and comparison script are not yet retained in the repository; see `results/verification-status.md` for attribution and auditability status.

## Pipeline and failure behaviour

1. Decode QUIC variable-length integers and parse supported long headers with bounds checks.
2. Derive Initial keys from the packet's destination connection ID using the v1 salt in RFC 9001 §5.2 and TLS 1.3 HKDF-Expand-Label construction.
3. Remove AES header protection before recovering the packet number; authenticate/decrypt with AES-128-GCM.
4. Parse the supported Initial frame subset to find CRYPTO ranges. Unknown frame types fail explicitly.
5. Insert CRYPTO ranges at protocol offsets; equal overlaps are accepted, conflicting overlaps rejected, and a size bound prevents unbounded allocation.
6. Return a handshake only when bytes from offset zero cover the declared ClientHello length, then validate the TLS structure and selected extensions.
7. For PCAP mode, report per-DCID candidate, decrypt, frame, reassembly, and completeness counts. Five additional candidate DCIDs per imported trace failed decryption but did not correspond to missed TShark ClientHellos in the reported 5/5 byte-set matches; their packet roles remain unclassified.

## Next engineering and research gates

- Preserve the user's `tls.handshake_raw` exports, exact TShark invocation, and byte-set comparison script/output. The exact comparison currently has user-reported rather than Arena-reproduced provenance.
- Add deterministic derived-PCAP tests for reversed/shuffled record order, selected Initial/CRYPTO loss, and truncation. Compare the current extractor and TShark on identical mutated inputs; record exact-byte recall, false-complete results, and explicit incomplete/decrypt-failed/unsupported dispositions.
- Extend C++ fixture coverage for IPv6, malformed/truncated records, VLAN/IP fragments, and packet-number/reassembly behavior under reordering.
- For the earlier registered pcapng QUIC baseline, establish a separate exact-byte result; the user's reported raw-byte check covers only `quic_chromium.pcap` and `quic_curl.pcap`.
- Verify JA4's QUIC protocol identifier and construction against a chosen reference before emitting any custom JA4.
- Promote the capture-quality-aware recovery direction to a contribution only if controlled measurements establish a material reproducible gap and the implementation measurably improves it. Check prior art and the course rubric; see `docs/original-contribution-plan.md`.
