# Verification status — Track 1 / Track 2 integration

## Cross-track verification (3 November 2026)

This record separates current-branch checks from imported teammate outputs and from user-reported WSL verification. Track 1 provenance remains provisional.

### Manifest and automated suites

- On the earlier pushed extraction commit, the user reports `make test` passed on Ubuntu WSL: CTest 1/1 and pytest 20/20. The user reports `make check` validated 16 records: 15 with packets, one empty, all 16 provisional, and `make eval` emitted `provisional_evidence`.
- Since then, the deterministic impairment harness and six Python tests were added. The expanded suite passes 26/26 locally with Python 3.11 and pytest 9.1.1. Rerun `make test`, `make check`, and `make eval` on the new branch head in WSL; the TShark-dependent impairment matrix also remains to be run there.
- The Python suite and C++ suite had also passed in the integration sandbox before the commit was pushed. The pushed branch is `arena/0d29f32c-cs331-phase2`.
- Imported raw/summary cross-check passed for hello counts, distinct JA3/JA4 counts, and reported TShark/FoxIO agreement. The repeated-Chromium `ja4-main` summary value cannot be recomputed because per-capture raw `ja4-main` output is absent.
- The Track 1 Docker/TShark/FoxIO analysis was not rerun as a full suite. The user's separate TShark raw-handshake check for the two QUIC captures is recorded below; it does not make the rest of the imported analyses independently reproduced.

### C++ PCAP extraction and raw-byte reference check

- The modular C++ targets built in the integration sandbox. CTest passed 1/1, including a synthetic classic-PCAP Ethernet/IPv4/UDP reader test and PCAPNG-magic rejection. The reader parsed the two QUIC captures as classic PCAP v2.4 Ethernet: Chromium had 140 packet records/UDP datagrams and curl had 148.
- The user reports the C++ CLI recovered five complete ClientHellos from each capture. Curl lengths were five times 1509 bytes. Chromium lengths were 1884, 1891, 1885, 1891, and 1880 bytes.
- **Exact-byte comparison: user-reported pass.** On Ubuntu WSL with TShark 4.6.4, GCC 15.2.0, and OpenSSL 3.5.5, the user reports extracting reassembled bytes using TShark's `tls.handshake_raw` field and obtaining 5/5 byte-identical matches for each PCAP (10/10 total). The comparison was by byte-string set equality because TShark's packet-arrival order differs from the C++ CLI's DCID-keyed output order.
- The raw `tls.handshake_raw` exports, exact TShark command, and comparison script/output have not yet been added to this repository. Therefore the result is attributed to the user's direct WSL run, not independently rerun or audited byte-by-byte in the Arena environment. Save the reference export and comparison command/output (or a privacy-reviewed machine-readable summary with hashes) to make this gate reproducible.
- The comparison status and provenance are recorded in `results/quic-extractor-comparison.json`. Full C++ hex logs, if present, are Git-ignored under `results/reproduced/`.

### L1 interpretation

The initial L1 concern was that QUIC v1 Initial protection or reference-tool coverage might prevent ClientHello extraction. These samples do not support that gap: the imported TShark/FoxIO reports expose five ClientHellos per capture, and the user-reported C++/TShark byte-set comparison reports 10/10 exact matches. This closes the clean-capture extraction check for these two traces; it does not prove broad support for all QUIC traffic, tools, or capture conditions.

### Remaining checks and contribution decision

- Preserve the user's raw reference export, exact command, output, and comparison script with provenance. Do not claim Arena independently reran the WSL byte comparison.
- The five additional candidate DCIDs per capture that the CLI reports as decrypt failures are not missed ClientHellos in this comparison: all ten TShark ClientHellos reportedly matched. Their packet roles remain to be classified before drawing any further conclusion.
- A provisional contribution direction is scaffolded in `docs/original-contribution-plan.md`: measure capture-quality-aware QUIC Initial recovery and completeness diagnostics under controlled record reordering, packet loss, and truncation. The clean-trace result establishes a baseline, not a gap or novelty claim. Continue only if controlled tests demonstrate a material, reproducible gap and an improvement over declared baselines; otherwise reject this direction.
- The imported T3 narrative/aggregate mismatch, missing T2 key log, empty T6 IPv6 capture, incomplete T7 DoH arm, and untraceable `ja4-main` raw result remain open. Docker/TShark/FoxIO full Track 1 reproduction remains separate from the reported raw-byte check.
