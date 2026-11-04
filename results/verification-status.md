# Verification status — Track 1 / Track 2 integration

**Updated:** 5 November 2026. This record separates (1) the user-run WSL batch now present in the repository, (2) imported Track 1/team outputs, and (3) checks performed on the committed artifacts in this checkout. The WSL run was not independently regenerated in Arena. Track 1 provenance remains provisional.

## WSL batch integrity and environment

The user generated `results/track2/verification-batch-20261104-201936/` from source commit `619a694a9fe449d97b4a54e487f0db7254b1fc08` on this branch. The directory was committed later as `00f34e4`. The repository-root SHA256 manifest check passed for all listed entries; the six key JSON groups (offload analysis, DCID inventory, preflight, and Chromium/curl case and result files) parsed successfully in this checkout.

Recorded environment: Ubuntu WSL2 Linux `6.18.33.2-microsoft-standard-WSL2`, TShark 4.6.4, GCC 15.2.0, OpenSSL 3.5.5, Python 3.14.4. The batch reports CTest **1/1**, pytest **39/39**, completed build, and 16 capture-manifest records (15 packet-bearing, one empty; all provisional). These are recorded WSL outcomes; do not call them an Arena rerun.

## QUIC byte comparison and bounded impairment matrix

The batch compares the C++ extractor and TShark on the same clean or mutated PCAP variant. Its JSON reports a byte-string multiset comparison, not packet-arrival order.

| Variant | curl: reference / extracted / exact match | Chromium: reference / extracted / exact match |
|---|---:|---:|
| Baseline | 5 / 5 / 5 | 5 / 5 / 5 |
| Reverse record order | 5 / 5 / 5 | 5 / 5 / 5 |
| Fixed-seed record shuffle | 5 / 5 / 5 | 5 / 5 / 5 |
| Drop one selected Initial-CRYPTO record | 5 / 5 / 5 | 5 / 5 / 5 |
| Drop every third selected Initial-CRYPTO record | 2 / 2 / 2 | 2 / 2 / 2 |
| Truncate selected record by 64 captured bytes | 5 / 5 / 5 | 5 / 5 / 5 |

Across the matrix: **54/54** TShark-emitted ClientHello byte strings matched, zero missed references, zero extra/nonreference outputs, exact-byte recall 1.0 in all 12 cells. Each client totals 27/27. The every-third-drop case is a 2/2 comparison against TShark on that damaged variant, not recovery of all five original handshakes. This bounded comparison does not make TShark independent ground truth or establish general QUIC support. Batch extractor logs also contain incomplete-flow/decryption-failure dispositions; these describe other candidate records and do not contradict exact matching of all complete reference ClientHellos.

The batch preserves `cases.json`, per-case variant PCAPs, TShark raw `jsonraw` exports, C++ logs, result JSON, and hashes. Earlier direct `tls.handshake_raw` exports and their separate comparison script were not saved as standalone artifacts; do not claim those separate exports are present. The batch's per-case artifacts support review of the bounded matrix.

### QUIC DCID context

The committed header inventory identifies five UDP flows in each capture. Each flow has an initial client DCID and later client Initial packet(s) whose DCID matches a server Initial SCID. The five extra per-DCID decryption-failure buckets are therefore later **client-to-server** Initials after a CID switch, not server-direction decrypt attempts. RFC 9001 §5.2 derives Initial secrets from the original client Initial DCID (with Retry-specific handling), while the current CLI derives from each packet's current DCID. This explains the extra buckets without demonstrating a missed ClientHello in these traces. See `docs/quic/implementation-status.md` and `results/track2/quic-initial-dcid-inventory.json`.

The bounded comparison shows no extraction/reordering/loss/truncation gap relative to TShark in tested conditions. QUIC recovery/reassembly is not supported as the original-contribution claim for these conditions.

## L3 SYN analysis and capture-vantage boundary

The WSL batch's TShark 4.6.4 analysis extracts six SYN observations across three complete streams in each of two separate offload PCAPs. Every client SYN has MSS/window-scale/window/TTL `1460/10/64240/64`; every peer SYN-ACK has `65495/7/65408/63`. IP length is 60 bytes, frame length 74 bytes, and the same-capture checker flags MSS, window-scale, and window asymmetry. The batch expressly says not to infer a proxy from one capture. These are two separate single-vantage traces, not paired observation points.

A separate user-reported container probe had peer MSS 1460 and was not visible on WSL `eth0`; that excludes this interface as the outer point for that reported probe if its filter/timing were correct. The Windows-side capture and the proposed Docker Desktop utility-VM path remain unavailable/unverified. MSS 65495 is not impossible, is not the path MTU, and does not prove a proxy or TCP termination. The imported T3 narrative/aggregate discrepancy and segmentation-offload effects still need separate treatment. See `docs/l3-contribution-plan.md` and `results/track2/l3-paired-probe-c28a486.md`.

## Imported Track 1 results: limits to retain

- **L2 / TLS secrets:** imported summary reports JA4X/JA4H count 0 without keys and 5 with keys in one TLS 1.3 sample. The key log is intentionally absent; keyed results are not reproducible here.
- **L4 / PQ:** imported raw output contains five ClientHellos per arm; TShark `tls.handshake.length` is 1511 vs 508, selected server groups 4588 vs 29, and JA4 values differ. This is one client/environment; JA4 changes with extension count/content and does not itself establish encoding of the selected group.
- **L5 / stability:** imported Chromium JSON has 50 ClientHellos, 50 JA3 values, and 15 released-path JA4 values; the `ja4_r` first signature-algorithm values are 15 GREASE-pattern codes. The report's `ja4-main=1` has no retained per-capture raw outputs and is not independently recomputable. Curl/Python each have 10 hellos and one released-path JA3/JA4. Do not generalize or promote to a new contribution.
- **L6 / IPv6:** `tls_ipv6.pcap` is an empty 24-byte PCAP header; the comparison is not applicable, not agreement.
- **L7 / ECH/DoH:** imported off/on page output says `sni=plaintext` / `sni=encrypted`. The packet JSON has five ClientHellos per ECH arm; ECH-off target SNI appears twice, and ECH-on public SNI `cloudflare-ech.com` appears twice. The imported report says plaintext DNS still exposes the target. ECH+DoH has 12 ClientHello rows for `cloudflare-dns.com`, but the target page output is empty; that arm is incomplete.
- Track 1 source context and tool provenance are recorded in `docs/track1-evidence-audit.md`. FoxIO's Rust CLI uses TShark, so its agreement is not independent packet decoding.

## Original-contribution status

- QUIC Initial recovery/reassembly: **not a contribution claim** for measured conditions; no extraction gap was shown relative to TShark in the bounded batch.
- L3 capture-vantage/JA4T attribution: **primary candidate to investigate, not a result**. Obtain synchronized evidence at a known boundary, correlate both legs, distinguish NAT from TCP termination, and keep TSO/GSO separate. Do not infer proxying from MSS/TTL or a single capture.
- Final contribution choice, course-rubric interpretation, and team approval remain open. See `DECISIONS.md`, `LEDGER.md`, `docs/landscape.md`, and `docs/l3-contribution-plan.md`.
