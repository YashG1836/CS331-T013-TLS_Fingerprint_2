# Verification status — Track 1 / Track 2 integration

## Cross-track verification (updated 4 November 2026)

This record separates current-branch checks from imported teammate outputs and from user-reported WSL verification. Track 1 provenance remains provisional.

### Manifest and automated suites

- On the earlier pushed extraction commit, the user reports `make test` passed on Ubuntu WSL: CTest 1/1 and pytest 20/20. The user reports `make check` validated 16 records: 15 with packets, one empty, all 16 provisional, and `make eval` emitted `provisional_evidence`.
- The user reports `make test` passed at commit `fec3b11` with 26 Python tests. After pulling that parser fix, this checkout passes 27/27 Python tests locally (Python 3.11, pytest 9.1.1); the added 27th test covers duplicate `tls.handshake_raw` JSON members. C++ sources were not changed by that parser fix or test addition.
- The Python suite and C++ suite had also passed in the integration sandbox before the commit was pushed. The pushed branch is `arena/0d29f32c-cs331-phase2`.
- Imported raw/summary cross-check passed for hello counts, distinct JA3/JA4 counts, and reported TShark/FoxIO agreement. The repeated-Chromium `ja4-main` summary value cannot be recomputed because per-capture raw `ja4-main` output is absent.
- The Track 1 Docker/TShark/FoxIO analysis was not rerun as a full suite. The user's separate TShark raw-handshake check for the two QUIC captures is recorded below; it does not make the rest of the imported analyses independently reproduced.

### C++ PCAP extraction and raw-byte reference check

- The modular C++ targets built in the integration sandbox. CTest passed 1/1, including a synthetic classic-PCAP Ethernet/IPv4/UDP reader test and PCAPNG-magic rejection. The reader parsed the two QUIC captures as classic PCAP v2.4 Ethernet: Chromium had 140 packet records/UDP datagrams and curl had 148.
- The user reports the C++ CLI recovered five complete ClientHellos from each capture. Curl lengths were five times 1509 bytes. Chromium lengths were 1884, 1891, 1885, 1891, and 1880 bytes.
- **Exact-byte comparison: user-reported pass.** On Ubuntu WSL with TShark 4.6.4, GCC 15.2.0, and OpenSSL 3.5.5, the user reports extracting reassembled bytes using TShark's `tls.handshake_raw` field and obtaining 5/5 byte-identical matches for each PCAP (10/10 total). The comparison was by byte-string set equality because TShark's packet-arrival order differs from the C++ CLI's DCID-keyed output order.
- The raw `tls.handshake_raw` exports, exact TShark command, and comparison script/output have not yet been added to this repository. Therefore the result is attributed to the user's direct WSL run, not independently rerun or audited byte-by-byte in the Arena environment. Save the reference export and comparison command/output (or a privacy-reviewed machine-readable summary with hashes) to make this gate reproducible.
- The comparison status and provenance are recorded in `results/quic-extractor-comparison.json`. Full C++ hex logs, if present, are Git-ignored under `results/reproduced/`.

### Impairment matrix and parser finding (user-reported)

The user reports running commit `fec3b11` on Ubuntu WSL with TShark 4.6.4 and seed 331. For each cell below the reported values are `reference / C++ extracted / exact-byte matched`, using TShark on that mutated capture as reference:

| Variant | curl | Chromium |
|---|---:|---:|
| Baseline | 5 / 5 / 5 | 5 / 5 / 5 |
| Reverse record order | 5 / 5 / 5 | 5 / 5 / 5 |
| Seeded record shuffle | 5 / 5 / 5 | 5 / 5 / 5 |
| Drop one selected Initial CRYPTO record | 5 / 5 / 5 | 5 / 5 / 5 |
| Drop every third selected Initial CRYPTO record | 2 / 2 / 2 | 2 / 2 / 2 |
| Truncate selected record by 64 captured bytes | 5 / 5 / 5 | 5 / 5 / 5 |

The user reports zero missed/extra outputs and no false-complete ClientHellos in all cases. The 2/2 every-third-drop result is recall against TShark's mutated-capture output, not recovery of all five original handshakes. The user describes three other flows as broken, but exact per-flow disposition counts and frame-to-flow mapping were not included in the report. Raw `impairment-results.json`, `cases.json`, and logs have not been added here; this remains user-reported, not independently reproduced in Arena.

The run found a harness bug: in the observed TShark `-T jsonraw` export, repeated `tls.handshake_raw` members occur at the same object level, and default Python `json.loads()` dictionary conversion retains only the last duplicate value. Commit `fec3b11` addresses this by scanning the raw export text for all matching values. The issue can be included as a bounded evaluation-pipeline finding; avoid claiming that all JSON parsing is unsafe or that this alone is a protocol contribution. A local regression test now verifies duplicate-value retention.

### L1 interpretation

The initial L1 concern was that QUIC v1 Initial protection or reference-tool coverage might prevent ClientHello extraction. These samples do not support that gap: the imported TShark/FoxIO reports expose five ClientHellos per capture, and the user-reported C++/TShark byte-set comparison reports 10/10 exact matches. This closes the clean-capture extraction check for these two traces; it does not prove broad support for all QUIC traffic, tools, or capture conditions.

### Remaining checks and contribution decision

- Preserve the user's raw reference export, exact command, output, and comparison script with provenance. Do not claim Arena independently reran the WSL byte comparison.
- The five additional candidate DCIDs per capture that the CLI reports as decrypt failures are not missed ClientHellos in this comparison: all ten TShark ClientHellos reportedly matched. Their packet roles remain to be classified before drawing any further conclusion.
- The reported impairment matrix shows no QUIC extraction/reordering/loss/truncation gap relative to TShark in the tested conditions. QUIC recovery is not the contribution candidate. A new C++ CLI change emits missing CRYPTO ranges for incomplete flows (and marks ranges as observed-extent-only when the declared handshake length is unknown); this code and its unit test still require `make test` and mutation-log verification on the user's WSL toolchain.
- L3 proxy-aware capture-vantage attribution is now the primary candidate to investigate, not a finding. Re-export SYN/SYN-ACK option rows from the imported offload captures, resolve the T3 narrative/aggregate discrepancy, and then choose paired capture points; separate TCP termination/vantage effects from TSO/GSO segmentation. See `docs/l3-contribution-plan.md`.
- The imported T3 narrative/aggregate mismatch, missing T2 key log, empty T6 IPv6 capture, incomplete T7 DoH arm, and untraceable `ja4-main` raw result remain open. Docker/TShark/FoxIO full Track 1 reproduction remains separate from the reported raw-byte check.
