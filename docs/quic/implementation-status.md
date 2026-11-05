# QUIC extraction implementation status

## Supported scope in the current increment

The C++ library supports QUIC v1 long-header packet-boundary parsing from UDP datagrams, client/server Initial secret derivation from a supplied destination connection ID, Initial header-protection removal, AES-128-GCM authentication/decryption, selected Initial frame parsing, offset-aware CRYPTO reassembly, and TLS ClientHello validation.

The key derivation is checked against the client Initial key/IV/header-protection values in RFC 9001 Appendix A.1. This unit vector is separate from end-to-end capture evidence.

The CLI accepts a UDP datagram as hex or a classic-PCAP v2.x Ethernet capture. The original PCAP mode remains available and filters client Initials by destination port. The new `--stateful-initial-context` mode reads UDP endpoints from unfragmented IPv4/IPv6, classifies client/server Initials by the selected service port, preserves the original client Initial DCID on a direction-normalized UDP 4-tuple, remembers server Initial SCIDs as switched-DCID aliases, and maintains separate client/server Initial packet-number contexts. It also reports the prior DCID-keyed client decrypt accounting beside stateful accounting. It does not handle PCAPNG, VLAN tags, IP fragments, IPv6 extension chains, QUIC v2, Retry transitions, tuple migration, 0-RTT decryption, all frame types, or JA4 calculation.

The user-run WSL batch at `results/track2/verification-batch-20261104-201936/` is now committed and its hashes/results JSON were inspected in this checkout. Across six cases per capture, the C++ output matched all 54 ClientHello byte strings emitted by TShark on the same PCAP variants (27/27 per trace; no misses/extras). The run itself was not independently regenerated in Arena, and TShark is the comparator rather than independent ground truth. The earlier standalone `tls.handshake_raw` export/script is not retained separately. See `results/verification-status.md`.

## Pipeline and failure behaviour

1. Decode QUIC variable-length integers and parse supported long headers with bounds checks.
2. In legacy mode, derive Initial keys from each packet's current DCID. In stateful mode, derive keys from the connection's original client Initial DCID, with client/server secrets selected by direction, using the v1 salt in RFC 9001 §5.2 and TLS 1.3 HKDF-Expand-Label construction.
3. Remove AES header protection before recovering the packet number; authenticate/decrypt with AES-128-GCM.
4. Parse the supported Initial frame subset to find CRYPTO ranges. Unknown frame types fail explicitly.
5. Insert CRYPTO ranges at protocol offsets; equal overlaps are accepted, conflicting overlaps rejected, and a size bound prevents unbounded allocation.
6. Return a handshake only when bytes from offset zero cover the declared ClientHello length, then validate the TLS structure and selected extensions.
7. Legacy PCAP mode reports per-DCID candidate/decrypt/frame/reassembly/completeness counts. Stateful mode reports Initial packet/decrypt/failure/context-miss totals by direction, per-connection metrics, and switched-DCID alias buckets separately from the number of client Initial packet records using those aliases. Incomplete ClientHellos report expected length and missing CRYPTO ranges where measurable; otherwise ranges are scoped to the observed extent. The committed header-only inventory establishes that the old extra DCID buckets are client-to-server packets using server-provided SCIDs, not server-direction attempts or missed ClientHellos. See `results/track2/quic-initial-dcid-inventory.json`.

## DCID handling and the five extra decrypt-failure buckets

A header-only inventory of the committed Chromium and curl PCAPs is reproducible with `code/scripts/quic_initial_inventory.py`; its complete output, input hashes, packet numbers, UDP endpoints, and DCID/SCID values are in `results/track2/quic-initial-dcid-inventory.json`. It finds five UDP flows per trace. In each flow, the first observed client-to-server Initial uses an 8-byte DCID; a later client-to-server Initial uses a distinct 20-byte DCID equal to the SCID observed in the server's Initial. For example, Chromium `172.17.0.2:36822` starts with DCID `97726dafe5a69bee` and later uses `01c803772feafd9e11ca9d7770eddf9e11b1e424`, which matches the server Initial SCID. The current extractor's five extra DCID buckets per trace therefore correspond to those later client packets.

**These are not five server-direction decrypt attempts.** `process_pcap()` currently selects only UDP datagrams whose destination port is 443 and derives `client in` keys from each packet's current DCID. That excludes server-to-client Initials (their source port is 443 and destination is the client's ephemeral port) and treats a later client Initial's switched DCID as if it were the original key-derivation input.

RFC 9001 §5.2 derives Initial secrets from the Destination Connection ID in the client's first Initial (the Original Destination Connection ID, absent a Retry-specific transition). A server-provided SCID does not retroactively change that secret. The old per-packet/per-DCID extractor therefore failed authentication for later client Initial packets addressed to a server SCID. This explains the extra buckets but did not reduce complete ClientHello extraction recall in the earlier runs: all five ClientHellos per capture byte-matched TShark.

The new implementation in `code/quic/src/initial_context.cpp` adds a bounded association on the direction-normalized IPv4/IPv6 UDP 4-tuple. It records the first client Initial's ODCID and client SCID; accepts later client Initial DCIDs only when they equal the ODCID or a server Initial SCID learned on that tuple; and verifies that a server Initial's DCID matches a client SCID before learning its SCID. Unknown CIDs do not replace the stored ODCID. Client and server Initial packet-number reconstruction state are separate. The stateful CLI additionally runs DCID-keyed client accounting on the same input so baseline successes/failures and alias buckets can be compared per connection without conflating packet records with distinct alias values.

This increment deliberately does not associate across tuple migration or implement the Retry ODCID transition. The WSL batch at `results/track2/verification-batch-20261105-105416/` was run against source commit `fa9fcdb` and committed in `03e89b8`. Its stateful captured-order baseline reports:

| Trace | Client Initials | Legacy client decrypt success / failure | Switched aliases / alias packets | Stateful client success / failure | Stateful server Initials success / failure | Baseline C++/TShark complete ClientHello byte matches |
|---|---:|---:|---:|---:|---:|---:|
| curl | 20 | 10 / 10 | 5 / 10 | 20 / 0 | 5 / 0 | 5 / 5, exact multiset |
| Chromium | 16 | 10 / 6 | 5 / 6 | 16 / 0 | 5 / 0 | 5 / 5, exact multiset |

The batch records CTest 1/1 and pytest 52/52. Each trace has five associations; baseline client/server context misses are zero. The byte comparison is an exact SHA-256 multiset comparison against TShark 4.6.4 on the same baseline PCAP, not an independent ground-truth test. The packet-level decrypt gains (+10 curl, +6 Chromium) do not increase ClientHello recall: the earlier stateless mode already emitted five complete hellos per baseline trace.

The stateful mutation matrix reveals order sensitivity: reverse-record-order matches 0/5 in each trace, shuffle matches 4/5, drop-one matches 5/5, every-third-drop 2/2, and truncation 5/5 (zero extras in each case). Thus the verified no-recall-regression statement is limited to the original captured order; it does not apply to reordered inputs. The older stateless matrix remains 27/27 per trace across its six cases.

Do not generalize the legacy prototype's per-packet DCID failures to Wireshark/TShark. TShark 4.6.4 is the byte comparator here, not the failing implementation. The batch preserves per-case commands, captures, JSON, raw TShark exports, per-connection/directional counters, and source hashes. This is inspectable user-run WSL evidence, not an independent Arena reproduction.

Source references: [RFC 9001 §5.2](https://www.rfc-editor.org/rfc/rfc9001.html#section-5.2); [RFC 9000 §7.2](https://www.rfc-editor.org/rfc/rfc9000.html#section-7.2). The packet inventory is independently generated from committed PCAP headers; the byte-set C++/TShark result is preserved in the user-run WSL batch and inspected in this checkout, but not independently regenerated in Arena.

## Next engineering and research gates

- The committed 5 November batch preserves per-case TShark `jsonraw` exports, C++ logs, variants, accounting JSON, and source hashes; the separate earlier `tls.handshake_raw` export/script is still not saved. The WSL execution is user-run and artifact-inspected, not independently regenerated in Arena.
- The batch records CTest 1/1 and pytest 52/52 on source commit `fa9fcdb`; the logs and per-connection/directional results are now in this checkout. A different environment is still needed for independent reproduction, and the Arena environment lacks CMake/OpenSSL development headers and live capture tools.
- The committed batch preserves the selected frames, mutation cases, variant PCAPs, raw TShark JSON, C++ logs, and result JSON. In the every-third-drop case, each tool reports two complete ClientHellos per trace; those are compared to each other, not to all five original hellos. The earlier baseline-assisted missing-range audit reports three incomplete statuses per trace, no trailing suffix for curl flow `d66102b4d71ac501`, and an additional Chromium suffix `[1026,1891)` for flow `896152443dcbf739` beyond the damaged capture's 1026-byte observed extent. When the damaged capture lacks a length header, observed-extent-only reporting is the correct uncertainty. See `results/verification-status.md` for provenance distinction.
- For the earlier registered pcapng QUIC baseline, establish a separate exact-byte result; the user's reported raw-byte check covers only `quic_chromium.pcap` and `quic_curl.pcap`.
- Verify JA4's QUIC protocol identifier and construction against a chosen reference before emitting any custom JA4.
- The earlier recovery/completeness-diagnostics contribution hypothesis remains rejected for the measured impairments. The narrower Initial connection/CID association is the current engineering result. Its captured-order baseline byte comparison is archived; its reverse/shuffle misses are also measured and must remain part of any claim. Novelty, rubric fit, and team approval remain open.
- L3 capture-vantage remains secondary: the committed batch contains three manual timing-based container/Wi-Fi pairs, but the bridge capture failed and the intermediary/mechanism is unresolved. See `docs/planning/l3-contribution-plan.md`.

## Future scope (not implemented or claimed complete)

1. **QUIC Retry transition.** Add RFC 9001 Retry integrity-tag validation and the Initial key-derivation transition using the Original Destination Connection ID. Test valid/invalid tags, retransmission ordering, and traces with/without Retry before claiming support.
2. **Connection-ID lifecycle across tuple changes.** Extend the current fixed-UDP-4-tuple association to authenticated CID updates and controlled NAT rebinding/migration traces. Define expiry/collision behavior and test client/server directions; do not treat an arbitrary tuple change or observed alias as proof of a migrated connection.
3. **L3 TCP-fingerprint attribution/normalization study.** Only revisit if new paired captures provide stronger, synchronized boundary evidence and a chosen JA4T/JA4TS reference implementation is validated. Separate observed profile differences from causes such as proxy termination, offload, or OS misclassification; current captures do not establish those mechanisms.
