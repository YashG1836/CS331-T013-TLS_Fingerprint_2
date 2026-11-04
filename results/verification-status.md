# Verification status — Track 1 / Track 2 integration

## Cross-track verification (updated 5 November 2026)

This record separates current-branch checks from imported teammate outputs and from user-reported WSL verification. Track 1 provenance remains provisional.

### Manifest and automated suites

- On the earlier pushed extraction commit, the user reports `make test` passed on Ubuntu WSL: CTest 1/1 and pytest 20/20. The user reports `make check` validated 16 records: 15 with packets, one empty, all 16 provisional, and `make eval` emitted `provisional_evidence`.
- The user reports `make build` and `make test` passed at commit `682051e` on Ubuntu WSL: CTest 1/1 and pytest 27/27, including duplicate-key parsing and missing-range tests. After adding the L3 checker, the user reports `python3 -m pytest -q` passed 36/36 at `c28a486`. In the later WSL batch run at `619a694`, the user reports `make build` completed with zero warnings, CTest passed 1/1, pytest passed 39/39, and the manifest validated 16 records (15 packet-bearing, one empty, all provisional). The user also reports TShark 4.6.4, GCC 15.2.0, OpenSSL 3.5.5, Linux 6.18, and exact-byte impairment recall 1.0 for both traces. The 39-test suite also passes locally (Python 3.11, pytest 9.1.1). The user's batch output files are not present in this shared checkout, so the latest run remains user-reported pending artifact transfer.
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

The user reports zero missed/extra outputs and no false-complete ClientHellos in all cases. The 2/2 every-third-drop result is recall against TShark's mutated-capture output, not recovery of all five original handshakes. In the latest batch, the user reports exact-byte recall 1.0 on both traces and generated `cases.json`, variant PCAPs, result JSON, logs, and hashes under `results/track2/verification-batch-20261104-201936/` in their WSL checkout. A follow-up audit reports three per-DCID incomplete statuses in each trace and supplies frame-to-flow/range mapping; see `docs/original-contribution-plan.md`. Those WSL batch files are not yet present in this shared checkout; the values remain user-reported, not independently inspected here.

The run found a harness bug: in the observed TShark `-T jsonraw` export, repeated `tls.handshake_raw` members occur at the same object level, and default Python `json.loads()` dictionary conversion retains only the last duplicate value. Commit `fec3b11` addresses this by scanning the raw export text for all matching values. The issue can be included as a bounded evaluation-pipeline finding; avoid claiming that all JSON parsing is unsafe or that this alone is a protocol contribution. A local regression test now verifies duplicate-value retention.

### L1 interpretation

The initial L1 concern was that QUIC v1 Initial protection or reference-tool coverage might prevent ClientHello extraction. These samples do not support that gap: the imported TShark/FoxIO reports expose five ClientHellos per capture, and the user-reported C++/TShark byte-set comparison reports 10/10 exact matches. This closes the clean-capture extraction check for these two traces; it does not prove broad support for all QUIC traffic, tools, or capture conditions.

### Remaining checks and contribution decision

- Preserve the user's raw reference export, exact command, output, and comparison script with provenance. Do not claim Arena independently reran the WSL byte comparison.
- A new header-only inventory of the committed QUIC PCAPs identifies the five additional per-DCID decrypt-failure buckets in each trace as later client-to-server Initial packets whose DCID matches the SCID from a server Initial (the post-switch CID). They are not server-direction decrypt attempts. The current client-only CLI filters UDP destination port 443 and derives Initial keys from each packet's current DCID; RFC 9001 §5.2 requires the connection's original client Initial DCID as the Initial-secret input (except the Retry transition). This explains the extra buckets without creating a missed-ClientHello finding; the user-reported 5/5 ClientHello matches remain conditional on the reported TShark comparison. See `docs/quic/implementation-status.md` and the committed header inventory.
- The reported impairment matrix shows no QUIC extraction/reordering/loss/truncation gap relative to TShark in the tested conditions. The user reports the missing-range audit found three incomplete statuses per trace without decrypt/frame/reassembly failures. Two flows per trace had declared ClientHello lengths and concrete gaps; the third was labeled `observed_extent_only`. Baseline correlation found no missing suffix for curl's unknown-length flow, and identified a Chromium suffix `[1026,1891)` beyond the damaged capture's observed extent. This is expected uncertainty, not a diagnostic misclassification: the mutated capture does not include the handshake length header. QUIC recovery/diagnostics is not supported as the contribution candidate for these tests.
- L3 proxy-aware capture-vantage attribution is the primary candidate to investigate, not a finding. On `c28a486`, the user reports TShark 4.6.4 analysis of both imported offload captures: six SYN/SYN-ACK observations over three complete streams per file, with the same client profile (MSS/window-scale/window/TTL 1460/10/64240/64) and peer profile (65495/7/65408/63) in each. The tool flagged MSS/window-scale/window asymmetry within each capture and did not pair the separate runs. The user-reported WSL inventory maps the default `172.17.0.0/16` network to `docker0`, currently DOWN; two other bridges and veths were UP, and the default route used WSL `eth0` (`192.168.38.227/20`). In a later user-reported paired probe, a container handshake (`172.17.0.3:42910 -> 104.16.123.96:443`) had peer MSS 1460 and option differences only in window scale/window; the flow was not seen on WSL `eth0`. This excludes that WSL interface as the outer point for that probe, but the user's Docker Desktop utility-VM explanation remains a topology hypothesis pending a Windows-side capture. The transcribed summary is in `results/track2/l3-paired-probe-c28a486.md`; raw PCAPs/JSON were not supplied. The T3 narrative/aggregate discrepancy remains; separate TCP termination/vantage effects from TSO/GSO segmentation. See `docs/l3-contribution-plan.md`.
- The imported T3 narrative/aggregate mismatch, missing T2 key log, empty T6 IPv6 capture, incomplete T7 DoH arm, and untraceable `ja4-main` raw result remain open. Docker/TShark/FoxIO full Track 1 reproduction remains separate from the reported raw-byte check.
