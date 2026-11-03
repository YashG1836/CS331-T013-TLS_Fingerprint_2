# Verification status — Track 1 / Track 2 integration

## Cross-track integration checks (3 November 2026)

This section records checks on the current working tree after the Track 1 archive import and the first PCAP-to-ClientHello CLI integration. It is separate from imported teammate logs and outputs.

### Track 1 evidence and Python suite

- `make check` passed for 16 hash-validated manifest records: 15 Track 1 attempts (14 with packet records and one empty IPv6 PCAP) plus the pre-existing `quic-v1-baseline-2026-11-03` record. Provenance remains provisional.
- `make eval` emitted `provisional_evidence`; it validates evidence records and hashes, not limitation conclusions.
- Python tests passed: 20/20.
- Imported raw/summary cross-check passed for hello counts, distinct JA3/JA4 counts, and reported TShark/FoxIO agreement. The repeated-Chromium `ja4-main` summary value cannot be recomputed because per-capture raw `ja4-main` output is absent.
- `results/preflight.json` remains the imported WSL snapshot; `make preflight` was not run to its default path. Docker, TShark, tcpdump, and FoxIO `ja4` are unavailable in this integration environment. `make lab-image`, `make lab-eval`, and fresh network captures were **not** run. Imported TShark/FoxIO output remains teammate-supplied.

### Current C++ core and PCAP extraction

- Built the current modular C++ targets with CMake 3.31.6 and OpenSSL 3.0.20 from temporary `/tmp` installations; neither dependency nor build artifact was added to the repository.
- CTest passed 1/1, including a synthetic classic-PCAP Ethernet/IPv4/UDP reader test and explicit PCAPNG-magic rejection. Pytest passed 20/20. `git diff --check` passed after these changes.
- The new classic-PCAP reader parsed the two imported QUIC files (classic PCAP v2.4, Ethernet) without unsupported records: `quic_chromium.pcap` had 140 records/UDP datagrams; `quic_curl.pcap` had 148.
- The connected CLI recovered five complete QUIC v1 ClientHellos from each capture. Five other candidate DCIDs per capture failed client-Initial decryption and remain unresolved; they were not counted as recovered.
- **Extent/framing comparison (not byte-for-byte comparison):** the imported TShark JSON reports Chromium handshake-body lengths `1876, 1880, 1881, 1887, 1887`; adding the four-byte TLS handshake header yields sorted total lengths `1880, 1884, 1885, 1891, 1891`. The C++ extractor recovered exactly that total-length multiset. The imported curl output reports five body lengths of `1505`; the extractor recovered five total ClientHellos of `1509` bytes. Each extracted sequence has ClientHello handshake type `1`, a declared TLS body length matching its recovered byte count, and parses successfully through the modular ClientHello parser.
- The imported TShark JSON has no full reassembled ClientHello byte arrays, and TShark was unavailable for a fresh raw export. Consequently **exact byte equality against an independent trusted reference has not yet been verified**. The current measurement corroborates counts, lengths, TLS framing, and parser validity only; JA3/JA4 outputs were not produced by the C++ CLI.
- The machine-readable length/framing result is tracked in `results/quic-extractor-comparison.json`. Full CLI output (including extracted ClientHello hex) is saved locally in Git-ignored `results/reproduced/quic_chromium_extractor.txt` and `results/reproduced/quic_curl_extractor.txt` and can be regenerated with the commands in `docs/track2-integration-plan.md`.

### Remaining verification gates

- In Ubuntu/WSL with TShark, export raw reassembled handshakes (commands in `docs/track2-integration-plan.md`) and compare bytes one-for-one in capture order. If `jsonraw` does not expose reassembled TLS bytes, use another trusted export path.
- Expand C++ fixture coverage for IPv6, truncated/invalid PCAP records, VLAN and IP fragments; test candidate-flow diagnostics and key updates under reordering/loss. Current CLI grouping is by DCID and destination port 443, not a complete bidirectional flow/migration model.
- Re-run Docker/TShark/FoxIO-dependent lab checks only in an environment where those tools are available. Preserve their outputs as reproduced results, distinct from the imported evidence.
