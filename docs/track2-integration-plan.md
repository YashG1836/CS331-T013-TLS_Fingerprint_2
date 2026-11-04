# Track 2 integration and validation plan

## Objective

Connect the modular C++ QUIC v1 core to Yash's `quic_chromium.pcap` and `quic_curl.pcap`, preserving the existing boundaries: `packet_parser`, `initial_crypto`, `frame_parser`, `crypto_reassembly`, and `client_hello`.

## Implementation and evidence status

1. **PCAP adapter — implemented.** `capture_reader` reads classic PCAP v2.x, Ethernet link type 1, and UDP payloads in unfragmented IPv4/IPv6. It rejects PCAPNG and non-Ethernet link types, and reports unsupported VLAN, fragment, and IPv6 extension-header cases. No libpcap dependency was added. The synthetic C++ test covers IPv4/UDP and PCAPNG-magic rejection; more malformed/truncated and IPv6 fixtures remain useful.
2. **Initial handling — works for the supplied clean traces, not a complete flow model.** The CLI filters on destination UDP port (443 by default), parses coalesced long-header packets, derives v1 client Initial keys, and groups state by DCID. It tracks the largest successfully recovered packet number per DCID. It does not yet model both directions, address/port tuples, DCID changes, migration, or multiple packet-number spaces comprehensively.
3. **CRYPTO reassembly and incomplete diagnostics.** Initial CRYPTO frames are fed to the offset-aware reassembler. The CLI reports per-DCID decrypt, frame, reassembly, and completeness counts. It now also reports the expected ClientHello length when the first four CRYPTO bytes are present and half-open missing ranges `[start,end)` for incomplete handshakes; if the length header is absent, ranges are explicitly limited to the observed extent. Five ClientHellos were recovered from each clean capture. Five other candidate DCIDs per capture produced decrypt failures; their packet roles remain unclassified.
4. **Clean-capture reference comparison — user-reported exact-byte pass.** The user reports a direct Ubuntu WSL run with TShark 4.6.4, GCC 15.2.0, and OpenSSL 3.5.5. TShark's `tls.handshake_raw` values were compared to the C++ recovered hex strings as unordered byte-string sets: 5/5 matched for Chromium and 5/5 for curl (10/10 total). TShark packet-arrival order differs from the CLI's DCID-keyed output order, hence set rather than positional comparison. The raw exports, exact command, and comparison script/output are not yet committed; this is user-reported, not independently reproduced in the Arena environment. See `results/verification-status.md` and `results/quic-extractor-comparison.json`.
5. **Tests and impairment runs — user-reported WSL results; latest range diagnostics need WSL validation.** The user reports the suite passed at commit `fec3b11` (26 Python tests) and reports running both PCAPs through the impairment harness with TShark 4.6.4, seed 331. All six cases per capture produced equal C++/TShark ClientHello multisets; detailed counts are recorded in `docs/original-contribution-plan.md`. The TShark run and JSON artifacts have not been independently reproduced or retained in this checkout. After the duplicate-key regression was added, the Python suite passed 27/27 locally (Python 3.11/pytest 9.1.1). The new C++ missing-range diagnostics and regression test now require `make test` on the user's WSL toolchain; this Arena environment lacks CMake and OpenSSL development headers.

## L1 interpretation

The clean captures do not show a QUIC v1 ClientHello extraction gap in the reference tools or in this C++ path: imported reference summaries report five hellos per trace, and the user-reported raw-byte set comparison matches all ten. This closes that specific clean-capture check, not broad support under impaired capture conditions. JA3/JA4 generation and independent full Track 1 tool reproduction remain separate.

## Current contribution direction and next checks

QUIC Initial recovery is rejected as the contribution for the tested matrix. The immediate QUIC follow-up is a bounded WSL diagnostic audit: re-run the `drop-every-third-initial-crypto-record` variant with the new missing-range output, map the selected original frames to DCIDs/CRYPTO offsets, and check each of the three absent original ClientHellos for an explicit incomplete status and the right range scope.

**Primary candidate to investigate: L3 proxy-aware capture-vantage attribution for JA4T/JA4TS.** The imported T3 observations are not yet a finding: raw SYN/SYN-ACK rows are absent, the MSS 65495 proxy interpretation is unverified, and the narrative frame sizes conflict with aggregate fields. First inspect the existing L3 PCAPs, then choose feasible paired capture points and separate proxy termination from TSO/GSO effects. See [`l3-contribution-plan.md`](l3-contribution-plan.md) for commands and gates. Check prior art and the rubric before claiming originality.

## Reproduction

Portable Ubuntu/WSL build, test, extraction, and `tls.handshake_raw` reference-export commands are in [`ubuntu-setup.md`](ubuntu-setup.md). The full imported Track 1 TShark/FoxIO lab rerun remains a separate optional check and can be run with `make lab-image` followed by `make lab-eval` where Docker is available.
