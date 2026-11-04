# Report status and evidence-backed draft material

**Status:** Draft material prepared; not a final report or team-approved conclusion. The deadline is 6 November 2026. Track 1 remains imported/team-supplied; the WSL verification batch is user-run and committed, and its hashes/JSON were inspected in this checkout but not regenerated in Arena. The comparison reference for the impairment matrix is TShark output from the same PCAP variant, not independent ground truth. Keep those provenance labels in the report.

## Provisional title and research framing

**Where protocol fingerprints stop: QUIC Initial extraction, TLS fingerprint variability, and TCP capture-vantage limits**

The project integrates a C++20 QUIC v1 Initial-to-ClientHello extractor and evaluates the limits of its evidence using bounded TShark comparisons and imported TLS/TCP experiments. The measured QUIC cases do not establish a novel recovery gap. The L3 question—whether a passive TCP fingerprint labels the endpoint visible at a capture boundary rather than the intended remote server—remains a candidate for controlled follow-up, not a demonstrated proxy detector or contribution.

## Executive results table

| Workstream | Evidence and metric | Supported result | Important boundary |
|---|---|---|---|
| Build and test | User WSL batch: GCC 15.2.0, OpenSSL 3.5.5, TShark 4.6.4, Linux 6.18.33.2 WSL2; CTest **1/1**, pytest **39/39**. Manifest: 16 capture records, 15 packet-bearing and one empty; all provisional. | Batch records a passing build/test run for the then-current branch source. | User-run batch; inspected in this checkout, not independently rerun in Arena. |
| QUIC byte comparison | 2 captures × 6 impairment cases; **54/54** complete TShark reference ClientHellos matched byte-for-byte as an unordered multiset; **0 misses, 0 extras**, recall 1.0 in every cell. Each capture totals 27/27; each every-third-drop variant has 2/2 outputs, not 5/5 original recovery. | No extraction/reassembly gap shown for these two captures and bounded cases. | TShark is the comparator on each same mutated PCAP. Does not establish broad QUIC correctness or independent ground truth. |
| QUIC connection-ID context | Header inventory: 5 UDP flows per trace; later client Initial DCIDs match server Initial SCIDs in each flow. | Explains 5 extra per-DCID failure buckets per trace as post-switch client packets under a per-packet DCID implementation. | Not server-direction decrypt failures; initial keys still require original client Initial DCID context (RFC 9001 §5.2). No missed ClientHello in these traces was demonstrated. |
| L3 SYN profile | Each of two separate offload PCAPs: 3 complete SYN/SYN-ACK pairs; client `1460/10/64240/64`, peer `65495/7/65408/63` (MSS/window scale/window/TTL); each frame 74 B; same-capture differences in MSS/window-scale/window. | Repeatable single-vantage option asymmetry in both traces. | Not paired vantage points; no proxy/termination inference. Analyzer explicitly warns against inferring a proxy from one capture. |
| L4 PQ vs classic | 5 ClientHellos per arm; TShark `tls.handshake.length` 1511 vs 508; server-selected groups 4588 vs 29; different JA4 output. | In this imported curl experiment, group selection correlates with a larger ClientHello and a different JA4. | One client/environment; JA4 change follows extension/count/hash differences, not proof that JA4 encodes the selected group. |
| L5 repeat stability | Imported Chromium JSON: 50 ClientHellos, 50 JA3, 15 released-path JA4; 15 distinct first signature-algorithm GREASE-pattern values. Reported `ja4-main` count is 1, but its raw per-capture records are absent. | Raw fields are consistent with GREASE variation contributing to released-path diversity. | Imported tool/source comparison; the `ja4-main` result cannot be recomputed; not a universal JA4 claim or a new contribution. |
| L7 ECH / DoH | ECH-off/on: 5 ClientHello rows each; target SNI appears in 2 off rows; `cloudflare-ech.com` appears in 2 on rows. Saved page outputs say `plaintext` vs `encrypted`. DoH pcap: 12 outer-SNI rows for `cloudflare-dns.com`; saved target page output empty. | Two team-supplied ECH page observations align with outer-SNI protection. | DoH target page not evidenced. Do not claim the ECH+DoH test succeeded or that all name leakage was eliminated. |

## Methods and evidence provenance

- The C++20 core parses supported QUIC v1 Initial packets, derives Initial keys, decrypts/authenticates packets, parses a supported Initial-frame subset, reassembles CRYPTO by offset, and validates ClientHello structures. It is intentionally not a full QUIC connection implementation and does not calculate JA4.
- Python provides deterministic PCAP mutation, comparison orchestration, evidence manifests, and conservative TCP SYN/SYN-ACK summaries. The WSL batch includes exact commands, hashes, per-case logs, variant PCAPs, TShark raw JSON exports, and result JSON.
- Track 1 T4/T5/T7 data remains teammate-supplied/imported. The empty IPv6 capture, missing TLS key log, and incomplete ECH+DoH page are not positive results.
- `results/verification-status.md`, `docs/track1-evidence-audit.md`, `docs/quic/implementation-status.md`, and `docs/l3-contribution-plan.md` carry detailed provenance and limits.

## Architecture diagrams

### QUIC v1 Initial-to-ClientHello analysis path

```text
classic PCAP
    │
    ▼
Ethernet → IPv4/IPv6 (bounded support) → UDP → QUIC v1 long header
                                                │
                         original client Initial DCID (RFC 9001 §5.2)
                                                │
                                                ▼
                          Initial key derivation / header protection
                                                │
                                                ▼
                                 AES-128-GCM authentication/decrypt
                                                │
                                                ▼
                                    supported Initial frames
                                                │
                                                ▼
                          CRYPTO ranges keyed by stream offset
                                                │
                           gaps / conflict / size-bound checks
                                                │
                                                ▼
                         complete TLS ClientHello byte validation
                                                │
                                                ▼
                    TShark same-variant byte-multiset comparison
```

The current CLI groups candidate records by each packet's current DCID; it does not yet track the connection's original DCID through the later CID switch. The header inventory explains the resulting extra buckets. Do not describe them as server-direction failures.

### L3 capture-vantage question (experimental layout, not established result)

```text
client/container ── inner TCP leg ── [bridge / VM / host boundary] ── possible outer leg ── remote service
       │                                      │                                │
       └─ capture A                           └─ capture B (required)           ┘

Compare paired SYN/SYN-ACK fields, 4-tuples, sequence numbers, timestamps,
interfaces, and timing. NAT may preserve one TCP handshake; a terminating
proxy creates separate TCP legs. A lone MSS/TTL or single capture is not proof.
```

The current imported offload PCAPs are two separate single-vantage traces. The separate reported container probe is absent from WSL `eth0`; a synchronized Windows/host-side capture remains required. Run TSO/GSO toggles separately from the vantage test.

## Results interpretation paragraphs ready for draft use

**QUIC:** “Across the two committed QUIC v1 traces and six deterministic variants per trace, the user-run WSL batch reports exact-byte multiset equality between the C++ extractor and TShark for all 54 ClientHellos emitted by the reference tool, with no extras. This is a bounded comparator result, not proof of broad QUIC conformance or an independent ground-truth measurement. No novel recovery gap was demonstrated.”

**L3:** “In each of two separate imported offload captures, three SYN/SYN-ACK pairs showed the same advertised client and peer TCP profiles. These are single-vantage observations; the batch analyzer expressly cautions against inferring a proxy from one capture. A separate user-reported probe did not appear on WSL `eth0`, so the outer path remains unobserved. Proxy termination and JA4T misattribution have not been established.”

## Limitations and remaining report gates

1. Maintain a provenance column in every results table: user-run WSL batch, imported Track 1, or independently rerun. Do not merge those labels.
2. State exact tested scope (two QUIC traces, six variants, one TLS client/environment per T4, one Chromium version/sample for T5, one site/browser for T7).
3. Keep L2 keyed results provisional; do not add or reproduce private key logs.
4. Keep L6 “not measured”; the IPv6 capture is empty.
5. Keep L7 ECH+DoH incomplete; the 12 DoH-hostname ClientHellos do not verify the target page load.
6. L3 requires paired, synchronized captures at known inner/outer points, proof of correlation, separation of NAT/termination, and TSO/GSO control. Do not claim `MSS=65495` proves a proxy.
7. Complete a targeted JA3/JA4/JA4T/p0f prior-art review and obtain team/rubric approval before selecting or naming an original contribution.

## Suggested final report structure

1. Research question and scope.
2. Background: TLS/QUIC visibility and fingerprint definitions (cite `docs/landscape.md`; fingerprint algorithms are not RFC standards).
3. System architecture and C++20/Python boundary.
4. Methods, versions, provenance, and bounded comparison protocol.
5. Results: QUIC, L3, then T4/T5/T7 with limitations attached to each table.
6. Discussion: no QUIC recovery contribution demonstrated; L3 remains an unproven candidate.
7. Threats to validity, missing evidence, and next controlled measurements.
8. Conclusion only after the team confirms contribution and rubric alignment.
