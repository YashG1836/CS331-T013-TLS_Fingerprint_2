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
7. For PCAP mode, report per-DCID candidate, decrypt, frame, reassembly, and completeness counts. For incomplete ClientHellos, report the declared expected byte length and missing half-open CRYPTO ranges when the first four bytes are present; otherwise label ranges as limited to the observed extent. A later header-only inventory classifies the five extra per-DCID failure buckets in each imported trace as client-to-server Initial packets using a post-switch DCID; they are not server-direction decrypt attempts and do not correspond to missed ClientHellos in the reported 5/5 byte-set matches. See `results/track2/quic-initial-dcid-inventory.json`.

## DCID handling and the five extra decrypt-failure buckets

A header-only inventory of the committed Chromium and curl PCAPs is reproducible with `code/scripts/quic_initial_inventory.py`; its complete output, input hashes, packet numbers, UDP endpoints, and DCID/SCID values are in `results/track2/quic-initial-dcid-inventory.json`. It finds five UDP flows per trace. In each flow, the first observed client-to-server Initial uses an 8-byte DCID; a later client-to-server Initial uses a distinct 20-byte DCID equal to the SCID observed in the server's Initial. For example, Chromium `172.17.0.2:36822` starts with DCID `97726dafe5a69bee` and later uses `01c803772feafd9e11ca9d7770eddf9e11b1e424`, which matches the server Initial SCID. The current extractor's five extra DCID buckets per trace therefore correspond to those later client packets.

**These are not five server-direction decrypt attempts.** `process_pcap()` currently selects only UDP datagrams whose destination port is 443 and derives `client in` keys from each packet's current DCID. That excludes server-to-client Initials (their source port is 443 and destination is the client's ephemeral port) and treats a later client Initial's switched DCID as if it were the original key-derivation input.

RFC 9001 §5.2 derives Initial secrets from the Destination Connection ID in the client's first Initial (the Original Destination Connection ID, absent a Retry-specific transition). The subsequent change to a server-provided connection ID, described by the QUIC connection-ID rules in RFC 9000 §7.2, does not retroactively change the Initial secret. Thus, later client Initial packets still require Initial keys derived from that connection's original DCID. The current per-packet/per-DCID implementation derives from the 20-byte switched DCID and predictably fails authentication for these packets. This explains the five extra buckets, but does not show a missing ClientHello in these captures: the user-reported C++/TShark comparison still matches all five complete ClientHellos per capture. A future bidirectional connection tracker would need to preserve the original DCID and choose the client/server Initial secret by direction; that is outside the current client-Initial ClientHello extraction scope.

Source references: [RFC 9001 §5.2](https://www.rfc-editor.org/rfc/rfc9001.html#section-5.2); [RFC 9000 §7.2](https://www.rfc-editor.org/rfc/rfc9000.html#section-7.2). The packet inventory is independently generated from the committed PCAP headers here; the byte-set C++/TShark result remains user-reported.

## Next engineering and research gates

- Preserve the user's `tls.handshake_raw` exports, exact TShark invocation, and byte-set comparison script/output. The exact comparison currently has user-reported rather than Arena-reproduced provenance.
- The user reports `python3 -m pytest -q` passed 36/36 in WSL at commit `c28a486`; earlier they reported CTest 1/1 at `682051e`. The full C++ suite was not rerun in Arena because CMake and OpenSSL development headers are unavailable.
- The user-reported `drop-every-third-initial-crypto-record` audit maps three incomplete flows per trace to missing ranges without decrypt/frame/reassembly errors. The subsequent baseline correlation found no trailing suffix for curl flow `d66102b4d71ac501` (1509-byte ClientHello, observed extent 1509), and an additional Chromium suffix `[1026,1891)` for flow `896152443dcbf739` (1891-byte ClientHello, observed extent 1026). The extractor correctly reports only observed-extent ranges when the damaged capture lacks the expected length. Raw mutation JSON/cases/logs remain unavailable in this checkout.
- For the earlier registered pcapng QUIC baseline, establish a separate exact-byte result; the user's reported raw-byte check covers only `quic_chromium.pcap` and `quic_curl.pcap`.
- Verify JA4's QUIC protocol identifier and construction against a chosen reference before emitting any custom JA4.
- QUIC recovery is not the contribution candidate for the measured conditions. L3 proxy-aware capture-vantage attribution is now the primary candidate to investigate. The user-reported paired probe has an inner container handshake, but WSL `eth0` does not contain the corresponding flow; no Windows-side outer leg establishes the peer's identity. Resolve the T3 aggregate/narrative discrepancy, preserve raw paired artifacts, and complete prior-art/rubric review before any contribution claim. See `docs/l3-contribution-plan.md`.
