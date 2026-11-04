# Track 2 integration and validation plan

## Objective

Connect the modular C++ QUIC v1 core to Yash's `quic_chromium.pcap` and `quic_curl.pcap`, preserving the existing boundaries: `packet_parser`, `initial_crypto`, `frame_parser`, `crypto_reassembly`, and `client_hello`.

## Implementation and evidence status

1. **PCAP adapter — implemented.** `capture_reader` reads classic PCAP v2.x, Ethernet link type 1, and UDP payloads in unfragmented IPv4/IPv6. It rejects PCAPNG and non-Ethernet link types, and reports unsupported VLAN, fragment, and IPv6 extension-header cases. No libpcap dependency was added. The synthetic C++ test covers IPv4/UDP and PCAPNG-magic rejection; more malformed/truncated and IPv6 fixtures remain useful.
2. **Initial handling — works for the supplied clean traces, not a complete flow model.** The CLI filters on destination UDP port (443 by default), parses coalesced long-header packets, derives v1 client Initial keys, and groups state by DCID. It tracks the largest successfully recovered packet number per DCID. It does not yet model both directions, address/port tuples, DCID changes, migration, or multiple packet-number spaces comprehensively.
3. **CRYPTO reassembly and incomplete diagnostics.** Initial CRYPTO frames are fed to the offset-aware reassembler. The CLI reports per-DCID decrypt, frame, reassembly, and completeness counts. It now also reports the expected ClientHello length when the first four CRYPTO bytes are present and half-open missing ranges `[start,end)` for incomplete handshakes; if the length header is absent, ranges are explicitly limited to the observed extent. Five ClientHellos were recovered from each clean capture. Five other candidate DCIDs per capture produced decrypt failures; their packet roles remain unclassified.
4. **Clean-capture reference comparison — user-reported exact-byte pass.** The user reports a direct Ubuntu WSL run with TShark 4.6.4, GCC 15.2.0, and OpenSSL 3.5.5. TShark's `tls.handshake_raw` values were compared to the C++ recovered hex strings as unordered byte-string sets: 5/5 matched for Chromium and 5/5 for curl (10/10 total). TShark packet-arrival order differs from the CLI's DCID-keyed output order, hence set rather than positional comparison. The raw exports, exact command, and comparison script/output are not yet committed; this is user-reported, not independently reproduced in the Arena environment. See `results/verification-status.md` and `results/quic-extractor-comparison.json`.
5. **Tests and impairment runs — user-reported WSL results; current local Python suite pass.** The user reports `make build` and `make test` passed at commit `682051e` on Ubuntu WSL (CTest 1/1, pytest 27/27), and reports running both PCAPs through the impairment harness with TShark 4.6.4, seed 331. All six cases per capture produced equal C++/TShark ClientHello multisets; the three loss-affected ClientHellos per capture were reported as incomplete with byte-range diagnostics. Subsequent clean-baseline matching shows no suffix for the unknown-length curl flow and an additional Chromium suffix `[1026,1891)` beyond observed extent; the damaged capture itself correctly cannot infer that total length. The new L3 tests bring the local Python suite to 36/36; WSL has not run them yet. Detailed user-reported counts are in `docs/original-contribution-plan.md`. Raw TShark artifacts have not been retained in this checkout.

## L1 interpretation

The clean captures do not show a QUIC v1 ClientHello extraction gap in the reference tools or in this C++ path: imported reference summaries report five hellos per trace, and the user-reported raw-byte set comparison matches all ten. This closes that specific clean-capture check, not broad support under impaired capture conditions. JA3/JA4 generation and independent full Track 1 tool reproduction remain separate.

## Current contribution direction and next checks

QUIC Initial recovery and completeness diagnostics are not contribution candidates for the tested matrix. The user reports three incomplete statuses per trace, and baseline correlation closes the unknown-length check: no curl suffix is missing, while Chromium has an additional baseline-relative suffix `[1026,1891)` beyond the damaged capture's observed extent. The extractor correctly labels that as unknowable from the damaged capture alone.

**Primary candidate to investigate: L3 proxy-aware capture-vantage attribution for JA4T/JA4TS.** The user reports SYN/SYN-ACK rows showing MSS 1460 versus 65495 and TTL 64 versus 63 in both offload captures. These single-vantage values do not establish proxy termination or make the MSS impossible; the raw TSV/PCAP is not retained here, and the T3 narrative frame sizes still conflict with aggregate fields. Next identify feasible paired capture points and separate proxy termination from TSO/GSO effects. See [`l3-contribution-plan.md`](l3-contribution-plan.md) for commands and gates. Check prior art and the rubric before claiming originality.

## Reproduction

Portable Ubuntu/WSL build, test, extraction, and `tls.handshake_raw` reference-export commands are in [`ubuntu-setup.md`](ubuntu-setup.md). The full imported Track 1 TShark/FoxIO lab rerun remains a separate optional check and can be run with `make lab-image` followed by `make lab-eval` where Docker is available.
