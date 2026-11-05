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

The committed header inventory identifies five UDP flows in each capture. Each flow has an initial client DCID and later client Initial packet(s) whose DCID matches a server Initial SCID. The legacy logs show five extra switched-DCID alias buckets per trace; Chromium has 16 client Initial records with 10 successes/6 failures, and curl has 20 with 10 successes/10 failures. These are later **client-to-server** packets, not server-direction attempts or missed ClientHellos. RFC 9001 §5.2 derives Initial secrets from the original client Initial DCID (with Retry-specific handling), while the legacy CLI derives from each packet's current DCID. See `docs/quic/implementation-status.md` and `results/track2/quic-initial-dcid-inventory.json`.

The earlier stateless extraction/reordering/loss/truncation comparison shows no gap relative to TShark in its tested conditions, so no broad recovery/recall contribution is claimed. The separate post-change stateful results below establish the captured-order baseline accounting and byte comparison, while revealing order sensitivity in the synthetic reorderings. Do not generalize the prototype's legacy per-packet DCID failures to Wireshark/TShark: TShark 4.6.4 is the same-PCAP comparator and emits five complete baseline ClientHellos per trace.

## Post-change WSL verification batch (5 November 2026)

The user ran the updated batch in Ubuntu WSL against source commit `fa9fcdb`; artifacts were committed in `7a2584c` at `results/track2/verification-batch-20261105-105416/`. This checkout has inspected the JSON/logs and verified the listed source-script SHA256 values, but has not independently regenerated the WSL run in Arena. The environment records TShark 4.6.4, GCC 15.2.0, OpenSSL 3.5.5, Python 3.14.4, and WSL Linux 6.18.33.2; `make-test.log` records CTest **1/1** and pytest **52/52**.

| Trace | Client Initial packets | Legacy DCID-keyed client decrypted / failed | Switched aliases / alias packets | Stateful client decrypted / failed | Stateful server Initials decrypted / failed | Baseline exact ClientHello byte match vs TShark |
|---|---:|---:|---:|---:|---:|---:|
| curl | 20 | 10 / 10 | 5 / 10 | 20 / 0 | 5 / 0 | 5/5; 0 misses, 0 extras |
| Chromium | 16 | 10 / 6 | 5 / 6 | 16 / 0 | 5 / 0 | 5/5; 0 misses, 0 extras |

The stateful baseline JSON records `multiset_equal=true`; the C++ and TShark SHA256 multisets are equal for each captured-order trace. Each has five UDP associations and zero client/server context misses. The gain is packet-level accounting (+10 curl and +6 Chromium client decrypts), not increased ClientHello recall. Five alias buckets are distinct DCID values; 10/6 are packet records.

The stateful synthetic matrix is order-sensitive: reverse-record-order matches **0/5** per trace; shuffle matches **4/5**; drop-one and truncate match **5/5**; every-third-drop matches **2/2** against TShark on that variant. There are zero extras. The “no recall regression” result therefore applies to the captured-order baseline only. The stateless matrix still reports 27/27 per trace across six cases. These are same-PCAP TShark comparisons, not independent ground truth.

The seven-row JSON reports L1/L2/L3/L4/L5/L7 artifact and live checks PASS. L6's public-egress artifact remains **NOT_MEASURED**; the optional local-loopback live check **FAIL** because tcpdump produced no packet-bearing IPv6 PCAP. The WSL uplink was reported to lack global IPv6 routing; `overall_live_status` is therefore FAIL, not a full seven-row live pass.

## L3 SYN analysis and capture-vantage boundary

The WSL batch's TShark 4.6.4 analysis extracts six SYN observations across three complete streams in each of two separate offload PCAPs. Every client SYN has MSS/window-scale/window/TTL `1460/10/64240/64`; every peer SYN-ACK has `65495/7/65408/63`. IP length is 60 bytes, frame length 74 bytes, and the same-capture checker flags MSS, window-scale, and window asymmetry. The batch expressly says not to infer a proxy from one capture. These are two separate single-vantage traces, not paired observation points.

The newer committed L3 batch has three manually correlated container/Wi-Fi pairs to `104.16.124.96:443`. Their distinct tuples and ISNs classify as `separate_tcp_legs_or_sequence_rewrite`; the vEthernet capture has no matching probe tuple, WSL `eth0` has two captured packets but no parsed SYN rows, and the bridge capture failed. The Wi-Fi capture is a host-adapter capture, not a physical-wire tap. These observations do not establish proxy identity or a particular termination/rewrite mechanism. MSS 65495 is absent from this paired run and belongs only to the older separate offload captures. The L3 review/manifest is documented in `docs/l3-contribution-plan.md`; the user-run captures are under `results/l3_paired_batch/`.

## Imported Track 1 results: limits to retain

- **L2 / TLS secrets:** imported summary reports JA4X/JA4H count 0 without keys and 5 with keys in one TLS 1.3 sample. The key log is intentionally absent; keyed results are not reproducible here.
- **L4 / PQ:** imported raw output contains five ClientHellos per arm; TShark `tls.handshake.length` is 1511 vs 508, selected server groups 4588 vs 29, and JA4 values differ. This is one client/environment; JA4 changes with extension count/content and does not itself establish encoding of the selected group.
- **L5 / stability:** imported Chromium JSON has 50 ClientHellos, 50 JA3 values, and 15 released-path JA4 values; the `ja4_r` first signature-algorithm values are 15 GREASE-pattern codes. The report's `ja4-main=1` has no retained per-capture raw outputs and is not independently recomputable. Curl/Python each have 10 hellos and one released-path JA3/JA4. Do not generalize or promote to a new contribution.
- **L6 / IPv6:** `tls_ipv6.pcap` is an empty 24-byte PCAP header; the comparison is not applicable, not agreement.
- **L7 / ECH/DoH:** imported off/on page output says `sni=plaintext` / `sni=encrypted`. The packet JSON has five ClientHellos per ECH arm; ECH-off target SNI appears twice, and ECH-on public SNI `cloudflare-ech.com` appears twice. The imported report says plaintext DNS still exposes the target. ECH+DoH has 12 ClientHello rows for `cloudflare-dns.com`, but the target page output is empty; that arm is incomplete.
- Track 1 source context and tool provenance are recorded in `docs/track1-evidence-audit.md`. FoxIO's Rust CLI uses TShark, so its agreement is not independent packet decoding.

## Original-contribution status

- Broad QUIC Initial recovery/reassembly: **not a contribution claim** for the measured conditions; no ClientHello recall gap was shown. Stateful Initial context/accounting is the **primary engineering result**: the captured-order baseline counters and exact TShark byte multiset are archived. The stateful reverse/shuffle misses are a measured limitation; novelty, rubric fit, and team approval remain open.
- L3 capture-vantage/JA4T attribution: **secondary limitation investigation, not a result**. Three timing-correlated pairs show distinct handshakes, but no termination mechanism or fingerprint misattribution is proven.
- Final contribution choice, course-rubric interpretation, and team approval remain open. See `DECISIONS.md`, `LEDGER.md`, `docs/landscape.md`, and `docs/l3-contribution-plan.md`.
