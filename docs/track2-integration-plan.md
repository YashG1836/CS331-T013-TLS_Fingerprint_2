# Track 2 integration and validation plan

## Objective

Connect the modular C++ QUIC v1 core to Yash's `quic_chromium.pcap` and `quic_curl.pcap`, preserving the existing boundaries: `packet_parser`, `initial_crypto`, `frame_parser`, `crypto_reassembly`, and `client_hello`.

## Implementation and evidence status

1. **PCAP adapter — implemented.** `capture_reader` reads classic PCAP v2.x, Ethernet link type 1, and UDP payloads in unfragmented IPv4/IPv6. It rejects PCAPNG and non-Ethernet link types, and reports unsupported VLAN, fragment, and IPv6 extension-header cases. No libpcap dependency was added. The synthetic C++ test covers IPv4/UDP and PCAPNG-magic rejection; more malformed/truncated and IPv6 fixtures remain useful.
2. **Initial handling — works for the supplied clean traces, not a complete flow model.** The CLI filters on destination UDP port (443 by default), parses coalesced long-header packets, derives v1 client Initial keys, and groups state by DCID. It tracks the largest successfully recovered packet number per DCID. It does not yet model both directions, address/port tuples, DCID changes, migration, or multiple packet-number spaces comprehensively.
3. **CRYPTO reassembly — exercised on both supplied traces.** Initial CRYPTO frames are fed to the offset-aware reassembler. The CLI reports per-DCID decrypt, frame, reassembly, and completeness counts. Five ClientHellos were recovered from each capture. Five other candidate DCIDs per capture produced decrypt failures; their packet roles have not been classified. They are not missed ClientHellos in the comparison below, since all ten reference ClientHellos reportedly matched.
4. **Clean-capture reference comparison — user-reported exact-byte pass.** The user reports a direct Ubuntu WSL run with TShark 4.6.4, GCC 15.2.0, and OpenSSL 3.5.5. TShark's `tls.handshake_raw` values were compared to the C++ recovered hex strings as unordered byte-string sets: 5/5 matched for Chromium and 5/5 for curl (10/10 total). TShark packet-arrival order differs from the CLI's DCID-keyed output order, hence set rather than positional comparison. The raw exports, exact command, and comparison script/output are not yet committed; this is user-reported, not independently reproduced in the Arena environment. See `results/verification-status.md` and `results/quic-extractor-comparison.json`.
5. **Tests — prior WSL pass; impairment harness added afterward.** The user reports `make test` passed on the byte-validation branch (CTest 1/1, pytest 20/20), `make check` passed for 16 records (15 with packets, 1 empty; all provisional), and `make eval` returned `provisional_evidence`. A new stdlib-only mutation/evaluation harness and six unit tests have since been added; its Python suite passes 26/26 locally (Python 3.11, pytest 9.1.1). The TShark-dependent variant run has not been executed here; rerun `make test` and the harness in WSL against this update.

## L1 interpretation

The clean captures do not show a QUIC v1 ClientHello extraction gap in the reference tools or in this C++ path: imported reference summaries report five hellos per trace, and the user-reported raw-byte set comparison matches all ten. This closes that specific clean-capture check, not broad support under impaired capture conditions. JA3/JA4 generation and independent full Track 1 tool reproduction remain separate.

## Original-contribution scaffold

Do not claim RFC-defined Initial decryption, the PCAP adapter, or clean-capture equality as novel. The provisional working direction is **capture-quality-aware QUIC Initial recovery and completeness diagnostics**. Establish a measurable gap before selecting this as the final contribution. The experiment plan, controls, metrics, and reject/continue gate are in [`original-contribution-plan.md`](original-contribution-plan.md).

The next measurement should compare the current extractor and TShark on deterministic derivatives of the two byte-validated captures: clean control, reversed/shuffled record order, selected packet/CRYPTO-record loss, and truncation. Record exact input hashes, per-case reference bytes, exact-byte recall, false-complete results, incomplete/decrypt-failed/unsupported dispositions, and runtime. Do not count the five unexplained candidate-DCID decrypt failures as missed ClientHellos without classifying those packets. If the controlled tests show no material gap or improvement, reject this candidate and reassess the other evidence-backed limitations. Check prior art and the course rubric with the team before any novelty claim.

## Reproduction

Portable Ubuntu/WSL build, test, extraction, and `tls.handshake_raw` reference-export commands are in [`ubuntu-setup.md`](ubuntu-setup.md). The full imported Track 1 TShark/FoxIO lab rerun remains a separate optional check and can be run with `make lab-image` followed by `make lab-eval` where Docker is available.
