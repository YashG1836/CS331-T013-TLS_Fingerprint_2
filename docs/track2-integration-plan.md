# Track 2 integration and validation plan

## Objective

Connect the modular C++ QUIC v1 core to Yash's `quic_chromium.pcap` and `quic_curl.pcap`, preserving the existing boundaries: `packet_parser`, `initial_crypto`, `frame_parser`, `crypto_reassembly`, and `client_hello`.

## Implementation and evidence status

1. **PCAP adapter — implemented.** `capture_reader` reads classic PCAP v2.x, Ethernet link type 1, and UDP payloads in unfragmented IPv4/IPv6. It rejects PCAPNG and non-Ethernet link types, and reports unsupported VLAN, fragment, and IPv6 extension-header cases. No libpcap dependency was added. The synthetic C++ test covers IPv4/UDP and PCAPNG-magic rejection; more malformed/truncated and IPv6 fixtures remain useful.
2. **Initial handling — works for the supplied clean traces, not a complete flow model.** The CLI filters on destination UDP port (443 by default), parses coalesced long-header packets, derives v1 client Initial keys, and groups state by DCID. It tracks the largest successfully recovered packet number per DCID. It does not yet model both directions, address/port tuples, DCID changes, migration, or multiple packet-number spaces comprehensively.
3. **CRYPTO reassembly, incomplete diagnostics, and DCID limitation.** Initial CRYPTO frames are fed to the offset-aware reassembler. The CLI reports per-DCID decrypt, frame, reassembly, and completeness counts, plus expected ClientHello length and half-open missing ranges when known. The committed header-only inventory classifies five extra failure buckets per trace as client-to-server Initials using a later DCID equal to the server Initial SCID. Initial secrets remain keyed from the connection's first client Initial DCID (RFC 9001 §5.2); the client-side destination-CID switch follows RFC 9000 §7.2. These are not server-direction decrypt attempts and did not cause missed ClientHellos in the reported test captures. The current CLI does not keep connection-level original-DCID context; see `docs/quic/implementation-status.md`.
4. **Clean and impaired comparison — WSL batch artifacts committed.** The user-run batch at `results/track2/verification-batch-20261104-201936/` records TShark 4.6.4, GCC 15.2.0, OpenSSL 3.5.5, CTest 1/1, and pytest 39/39. Its six cases per trace report exact-byte multiset equality: 27/27 for Chromium, 27/27 for curl; 54/54 total, zero misses/extras. The every-third-drop case is 2/2 per trace against TShark on the same damaged variant. Artifacts and hashes were inspected in this checkout, but the WSL run was not regenerated in Arena and TShark is not independent ground truth. The separate earlier `tls.handshake_raw` export/script is not retained as a standalone artifact.
5. **Incomplete diagnostics and DCID context.** Batch impairment artifacts and JSON are present. A separate baseline-assisted diagnostic audit reports three incomplete statuses per trace; curl has no missing suffix beyond observed extent, while Chromium has a baseline-relative suffix `[1026,1891)` beyond the damaged capture's 1026-byte observed extent. Unknown expected length is correctly not inferred from damaged data. The header inventory identifies five later client Initial DCIDs per trace matching a server Initial SCID; these are post-switch client packets, not server-direction decrypt attempts. See `docs/quic/implementation-status.md` and `results/verification-status.md`.

## L1 interpretation

The clean and bounded impaired captures do not show a QUIC v1 ClientHello extraction gap relative to TShark: the committed user-run batch reports 54/54 byte-identical reference outputs across two traces and six cases. This closes only those comparator checks, not broad support under impaired capture conditions or independent ground truth. JA3/JA4 generation and full Track 1 tool reproduction remain separate.

## Current contribution direction and next checks

QUIC Initial recovery and completeness diagnostics are not contribution candidates for the tested matrix. The user reports three incomplete statuses per trace, and baseline correlation closes the unknown-length check: no curl suffix is missing, while Chromium has an additional baseline-relative suffix `[1026,1891)` beyond the damaged capture's observed extent. The extractor correctly labels that as unknowable from the damaged capture alone.

**Primary candidate to investigate: L3 capture-vantage attribution for JA4T/JA4TS.** The committed WSL batch contains TShark JSON and reports three SYN/SYN-ACK pairs per separate offload capture: MSS 1460 vs 65495, TTL 64 vs 63, with window-scale/window differences as well. These are single-vantage observations, not paired legs; the checker explicitly warns against proxy inference from one capture. MSS 65495 is not impossible or proxy proof. The separate controlled probe's corresponding flow was absent from WSL `eth0`; a Windows/host-side capture is still needed. Keep the T3 narrative/aggregate discrepancy and TSO/GSO effects separate. See [`l3-contribution-plan.md`](l3-contribution-plan.md); prior-art and rubric review remain open.

## Reproduction

Portable Ubuntu/WSL build, test, extraction, and `tls.handshake_raw` reference-export commands are in [`ubuntu-setup.md`](ubuntu-setup.md). The full imported Track 1 TShark/FoxIO lab rerun remains a separate optional check and can be run with `make lab-image` followed by `make lab-eval` where Docker is available.
