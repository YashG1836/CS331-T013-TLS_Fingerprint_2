# Where Protocol Fingerprints Stop
## Stateful QUIC Initial Accounting and Capture-Vantage Limits

**CS331 Phase 2 — presentation draft**

**Authors:** [insert approved team member names]

**Status:** Draft deck aligned with the project’s agreed engineering/evaluation contribution framing; final course-rubric review and submission sign-off remain open.

> **Persistent evidence labels:** `WSL BATCH — user-run, artifacts committed/inspected; not independently reproduced in Arena` and `TRACK 1 — imported/team-supplied`. TShark 4.6.4 is the same-PCAP comparison reference, not independent ground truth.

---

## Slide 1 — Research question

**When does a passive fingerprint describe the observed network leg rather than the intended endpoint?**

- Primary depth dive: QUIC v1 Initial packet accounting and ClientHello extraction.
- Secondary investigation: TCP capture vantage and fingerprint attribution limits.
- Result framing: CID/state tracking is established QUIC-stack and analyzer practice, not the novelty claim.
- Project contribution: the proposal’s “measured map plus one first step”—demonstrate a lightweight extractor’s packet-accounting blindspot, then design, implement, and evaluate `InitialContextAssociator`.

**Speaker notes:** Keep focus on what a sensor can observe. A fingerprint is not an identity guarantee. The contribution is an engineering/evaluation result for lightweight passive extractors, not invention of stateful CID tracking as a QUIC protocol mechanism. Fill in approved team names/course details.

**Evidence cue:** `report/report.md`, `DECISIONS.md`.

---

## Slide 2 — Why QUIC Initial context matters

```text
Client Initial: DCID = original client Initial DCID (ODCID)
Server Initial: SCID = server-issued connection ID
Later client Initial: current DCID may equal that server SCID

Initial secrets still use the Initial key context—not a fresh key from every current DCID.
```

- The earlier C++ prototype derived Initial keys independently from each packet's current DCID.
- The five switched-DCID buckets per trace were later **client-to-server** packets.
- They were not server-direction failures and did not imply missing ClientHellos.

**Speaker notes:** RFC 9001 §5.2 defines the Initial key schedule and Retry-specific transition. The 16 failures in the old table are from our prototype's stateless per-DCID accounting only. In a separate WSL check, the user reports zero `quic.decryption_failed` matches from TShark on both original captures, including post-switch DCIDs; the command output is not archived in the batch. Present TShark/Wireshark as the stateful reference, not as failing.

**Sources:** [RFC 9001 §5.2](https://www.rfc-editor.org/rfc/rfc9001.html#section-5.2), per-trace header inventory in `results/track2/verification-batch-20261105-105416/quic-initial-dcid-inventory.json`.

---

## Slide 3 — Bounded stateful associator

```text
classic PCAP → Ethernet/IP/UDP → QUIC v1 Initial
                                │
      direction-normalized UDP 4-tuple
      ├── retain original client Initial DCID
      ├── validate direction and learn server Initial SCID aliases
      └── separate client/server packet-number contexts
                                │
                   Initial decrypt → CRYPTO reassembly
                                │
                      complete ClientHello bytes
```

- Reports stateful and legacy DCID-keyed client accounting side by side.
- Five observed UDP associations per trace in the baseline batch.
- Not a complete QUIC connection tracker; Retry (`retry_packets_observed_unsupported`) and tuple migration/rebinding are unsupported.
- CID mechanics are specified in RFC 9000/9001 and stateful tracking is established practice in full stacks/analyzers; this project does not claim to invent it.

**Speaker notes:** The “fixed 4-tuple” bound is essential. This is not full RFC 9001 compliance and does not cover CID migration, NAT rebinding, PCAPNG, VLANs, fragments, or QUIC v2.

**Sources:** `code/quic/src/initial_context.cpp`, `docs/quic/implementation-status.md`.

---

## Slide 4 — Evaluation and provenance

- Two committed baseline traces: curl and Chromium.
- Six deterministic cases per trace: baseline, reverse order, shuffle, drop one selected Initial-CRYPTO record, drop every third selected record, truncate a selected record.
- Byte comparison uses a **multiset of complete ClientHello bytes** from C++ and TShark on the **same PCAP variant**.
- WSL QUIC batch: TShark 4.6.4, GCC 15.2.0, OpenSSL 3.5.5, Python 3.14.4. Docker `cn-lab` Track 1: TShark 4.4.19; FoxIO `ja4` tag `v0.18.6` reports 0.18.5, while `ja4-main` reports 0.18.6.
- Build/tests: CTest **1/1**, pytest **52/52**.

**Evidence label:** `WSL BATCH — user-run; source commit fa9fcdb; batch committed in 7a2584c`.

**Speaker notes:** Batch files, logs, variant PCAPs, raw TShark exports, JSON, and script hashes are in `results/track2/verification-batch-20261105-105416/`. We inspected the artifacts and source hashes in this checkout, but did not rerun the WSL experiment in Arena. Keep WSL and Docker versions/results separate; the FoxIO tag and reported binary version are not interchangeable labels.

---

## Slide 5 — Baseline packet accounting

| Trace | Client Initials | Legacy client decrypts / failures | Stateful client decrypts / failures | Stateful server Initials decrypts / failures | Alias buckets / packets |
|---|---:|---:|---:|---:|---:|
| curl | 20 | 10 / 10 | **20 / 0** | 5 / 0 | 5 / 10 |
| Chromium | 16 | 10 / 6 | **16 / 0** | 5 / 0 | 5 / 6 |

- Improvement in prototype packet accounting: **+10** curl and **+6** Chromium client Initial decryptions.
- Baseline context misses: zero, both directions; five associations per trace.

**Speaker notes:** Five alias buckets are five distinct DCID values. Ten and six are client packet records using those aliases. Do not label these as lost ClientHellos or server-direction attempts.

**Generated from:** `report/build_report.py`; primary JSONs at `quic-stateful/{curl,chromium}/impairment-results.json`.

---

## Slide 6 — Baseline bytes match; counts are not bytes

| Trace | Complete ClientHellos | Exact byte multiset vs TShark 4.6.4 | Misses / extras |
|---|---:|---:|---:|
| curl | 5 | **5/5** | 0 / 0 |
| Chromium | 5 | **5/5** | 0 / 0 |

- Per-trace JSON records `multiset_equal=true` and matching SHA-256 multisets.
- This establishes baseline captured-order byte agreement with TShark—not independent ground truth, broader conformance, or increased recall.
- The earlier stateless extractor also emitted 5/5 for both baseline traces: packet accounting improves, but baseline ClientHello recall does not.
- User-reported frame audit: each complete ClientHello was already wholly present in pre-switch datagrams in these captures; the frame map is not archived yet. This is trace-specific, not a general claim that later Initial packets cannot carry ClientHello bytes.

**Speaker notes:** Do not conflate complete-hello counts with byte identity; here we have both the count and a byte-multiset comparison. The comparator and C++ extractor consumed the same PCAP.

---

## Slide 7 — The stateful mode is order-sensitive

| Case | curl matched | Chromium matched |
|---|---:|---:|
| Baseline captured order | 5/5 | 5/5 |
| Reverse record order | **0/5** | **0/5** |
| Shuffle record order | **4/5** | **4/5** |
| Drop one Initial-CRYPTO record | 5/5 | 5/5 |
| Drop every third selected record | 2/2 | 2/2 |
| Truncate selected record | 5/5 | 5/5 |

- All listed cases have zero extra ClientHellos; reverse/shuffle miss reference outputs.
- The stateless matrix remains **27/27 per trace** across six cases.
- Therefore “no recall regression” is supported for the **captured-order baseline only**, not for reordered records.

**Speaker notes:** This is the key qualification discovered in the committed batch. The associator is a single-pass input-record-order tracker: the first observed client Initial seeds the presumed original DCID; the server SCID alias is learned only after the matching server Initial is processed. Reverse order places switched-DCID client packets before that announcement and before the true original Initial; the first switched DCID seeds the wrong context. With no buffering or timestamp-based reordering, alias resolution is unavailable when needed, producing 0/5; shuffle retains enough context for 4/5. A timestamp-aware pre-pass or bounded buffering/deferred association is future work, not implemented. This is a prototype order limitation, not a TShark/Wireshark failure.

**Generated from:** stateful `impairment-results.json` files in the committed batch.

---

## Slide 8 — Seven-row status and IPv6 limit

- L1, L2, L3, L4, L5, L7: artifact and requested live checks **PASS** in the batch JSON.
- L6 artifact: **NOT_MEASURED** for public IPv6 egress; this scope is accepted. The committed PCAP contains only a PCAP header.
- Optional local `::1` control: **FAIL**—tcpdump produced no packet-bearing IPv6 PCAP; it is not a public-egress measurement.
- Overall artifact status: **INCOMPLETE**; overall live status: **FAIL**.

**Speaker notes:** L6 is accepted as NOT_MEASURED for public IPv6 egress. The WSL uplink was reported to lack a global IPv6 route. The local loopback control failed to produce a packet-bearing PCAP and does not count as public egress. Do not say L6 was measured.

**Evidence:** `results/track2/verification-batch-20261105-105416/seven-rows-live.json` and `.log`.

---

## Slide 9 — Secondary fingerprint observations: bounded claims

- **L3:** selected container/Wi-Fi observations have distinct tuples and initial sequence numbers; consistent with separate TCP legs or sequence rewrite. No proxy identity, termination mechanism, OS misclassification, or JA4T/JA4TS error is established.
- **L4/L5/L7:** imported/team-supplied TLS samples show configuration-linked fingerprint differences, GREASE-associated variability, and ECH outer-name observations within narrow sample scopes.
- **L2:** one imported/team-run TLS 1.3 sample reports **0 JA4X/JA4H outputs without session secrets vs 5 with secrets** (4 JA4X certificate-chain entries + 1 JA4H). The key log is intentionally absent; this is sample-scoped evidence, not an independently reproducible or universal result.
- **L6:** public IPv6 egress is accepted as **NOT_MEASURED**; the local `::1` control failed and is not a substitute.

**Speaker notes:** Keep Track 1 labels visible. The complete row-level values and source caveats are in `LEDGER.md` and `docs/track1-evidence-audit.md`. A DoH target-page arm is incomplete; the ECH observations do not establish broad privacy guarantees.

---

## Slide 10 — Validity, scope, and takeaway

**Project contribution — measured map plus one first step:** The stateless prototype’s per-current-DCID accounting misses 10 curl + 6 Chromium client Initial packets. The C++ `InitialContextAssociator` applies original-DCID/SCID-alias context aligned with RFC 9001 §5.2, decrypts 16 additional packets with zero client failures in the tested captured-order traces, and matches complete ClientHello bytes 5/5 per trace against TShark 4.6.4. This is an engineering/evaluation contribution for lightweight passive extractors—not a new QUIC CID protocol mechanism.

**Not supported:**
- General QUIC correctness or order-independent recovery.
- Full RFC 9001 conformance, Retry, or connection migration.
- Wireshark/TShark failure, proxy identification, or JA4T misattribution.
- Global novelty of stateful CID tracking, full RFC coverage, public IPv6 measurement, broad privacy, or course-rubric completion.

**Speaker notes:** This is the project’s approved engineering/evaluation framing: a measured map of the accounting blindspot plus one implemented first step. Keep the distinction between packet-accounting improvement and ClientHello recall explicit, and do not claim the protocol mechanism itself is new.

---

## Slide 11 — Next work and decision gates

1. Add testable QUIC Retry integrity and Initial key transition.
2. Extend authenticated CID lifecycle to controlled tuple migration/NAT rebinding.
3. Improve order-robust context establishment with bounded buffering and regression tests.
4. For L3, collect synchronized captures at known boundaries before attributing causes or considering normalization.
5. Complete targeted prior-art and rubric review; confirm that the adopted engineering/evaluation framing satisfies the course contribution criterion.

**Future scope, not current claims.**

---

## Slide 12 — References and discussion

- RFC 9001 §5.2 — QUIC Initial key derivation: <https://www.rfc-editor.org/rfc/rfc9001.html#section-5.2>
- RFC 9000 §7.2 — Connection IDs: <https://www.rfc-editor.org/rfc/rfc9000.html#section-7.2>
- FoxIO JA4 v1.0.1 implementation reference: <https://github.com/FoxIO-LLC/ja4/releases/tag/v1.0.1>
- WSL QUIC reference: TShark 4.6.4; Docker `cn-lab`: TShark 4.4.19, FoxIO `ja4`/`ja4-main` version labels differ. See `docs/track1-evidence-audit.md` and `results/track2/verification-batch-20261105-105416/`. User-reported zero-failure filters are supplemental and not archived.
- Google QUICHE: <https://github.com/google/quiche>; ngtcp2: <https://github.com/ngtcp2/ngtcp2>; Wireshark: <https://github.com/wireshark/wireshark> (illustrative stateful implementations/analyzer; not a systematic prior-art review).
- Full methods, generated tables, threats to validity, and references: `report/report.md`

**Discussion prompt:** How does the measured-map-plus-first-step engineering contribution differ from claiming a new QUIC protocol mechanism, and what does its order-sensitive evaluation teach us?
