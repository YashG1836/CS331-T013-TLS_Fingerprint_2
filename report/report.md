# Where Protocol Fingerprints Stop: Stateful QUIC Initial Accounting and Capture-Vantage Limits

**CS331 Phase 2 — formal report draft**

**Authors:** [insert approved team member names]

**Date:** 5 November 2026
**Status:** Submission draft aligned with the project’s agreed engineering/evaluation contribution framing; final course-rubric review and submission sign-off remain open.

> **Evidence note.** Quantitative QUIC tables below are generated from the committed WSL batch by `python3 report/build_report.py`. The 5 November stateful execution used Ubuntu WSL (GCC 15.2.0, Python 3.14.4, OpenSSL 3.5.5, TShark 4.6.4), was run against source commit `fa9fcdb`, and was committed with its artifacts in `7a2584c`. It is inspectable here but was not independently regenerated in Arena. The separate Docker `cn-lab` Track 1 environment records TShark 4.4.19; its FoxIO `ja4` built from tag `v0.18.6` reports binary version 0.18.5, while `ja4-main` at commit `c6469a7` reports 0.18.6. Keep those toolchains and results distinct. Track 1 TLS observations remain imported/team-supplied. TShark is a same-PCAP stateful reference/comparator, not an independent ground-truth oracle.

## Abstract

Passive protocol fingerprints describe fields visible at a particular network capture point; they do not, by themselves, identify a user, application, or ultimate server behind an intermediary. The project’s engineering/evaluation contribution for lightweight passive extractors is the design, implementation, and bounded evaluation of the C++ `InitialContextAssociator`. It demonstrates an avoidable packet-accounting blindspot in the prototype’s stateless per-current-DCID baseline (10/20 curl and 10/16 Chromium client Initials decrypted), then applies original-DCID context and server-SCID aliases in line with RFC 9001 §5.2: the stateful mode decrypts 20/20 and 16/16 client Initials (16 additional packets total, zero failures) and matches the five complete ClientHellos per trace byte-for-byte against TShark 4.6.4. This is not a claim that stateful CID tracking is a new QUIC protocol mechanism. The evaluation also characterizes the input-order boundary: reverse record order yields 0/5 matches and shuffle 4/5. The second depth dive is passive visibility: the team-reported L2 comparison yielded 0 JA4X/JA4H outputs without TLS session secrets versus 5 with secrets (four certificate-chain JA4X entries and one JA4H) for one TLS 1.3 curl sample; its key log is not committed, so this result is not independently reproducible from this repository. The auxiliary L3 evidence does not establish proxy termination or fingerprint misattribution. Public IPv6 egress remains NOT_MEASURED by accepted scope; the local `::1` control did not produce a packet-bearing PCAP.

**Keywords:** QUIC Initial, connection ID, ClientHello, protocol fingerprint, capture vantage, TShark, evidence provenance.

## 1. Introduction

Transport and TLS fingerprints are summaries of observable protocol fields. Their meaning depends on which leg is captured, which messages are visible, and how the tool normalizes those fields. A SYN profile describes the TCP endpoint visible at that capture point. A ClientHello fingerprint describes the ClientHello visible on that TLS leg. Neither necessarily identifies the intended remote application endpoint when a TCP/TLS-terminating intermediary exists; conversely, one unusual MSS, TTL, or fingerprint is not proof that such an intermediary exists [4].

QUIC adds a specific packet-accounting question. A QUIC v1 Initial's packet protection can be derived from public version and connection-ID inputs. RFC 9001 §5.2 defines the Initial key schedule around the original client Initial DCID (with a Retry-specific transition) [1]. A later client Initial can use a server-provided SCID as its current DCID without changing the original Initial secret. The project's earlier C++ prototype derived keys independently from each packet's current DCID, creating decrypt-failure buckets for such later client packets even though its complete ClientHello outputs matched TShark in the original traces.

The contribution is a project-specific engineering/evaluation result: a measured stateless accounting blindspot, the `InitialContextAssociator` as a first implementation step, and an evaluation of its correctness and ordering limit on the available traces. RFC-defined CID mechanics are not claimed as a protocol invention. QUIC is the primary depth dive; passive visibility is the second, while L3 remains secondary. This report does not claim full QUIC conformance or proxy detection.

### Research questions

1. Does retaining QUIC v1 Initial context across a stable UDP four-tuple eliminate the prototype's post-switch client Initial decrypt failures in the captured-order curl and Chromium traces?
2. For those traces, do the stateful ClientHello bytes match TShark 4.6.4, and what does the deterministic record-order matrix reveal about statefulness limits?
3. What does the passive-visibility comparison show about JA4X/JA4H with and without session secrets, and what do the supporting TCP/TLS experiments not establish?

## 2. Background

QUIC connection IDs support routing and connection continuity, but the Initial key derivation rule is tied to the original Initial DCID rather than an arbitrary later packet's DCID [1, 2]. Therefore, a packet-level extractor needs state to associate packets and direction. This project implements a deliberately bounded state model: a direction-normalized IPv4/IPv6 UDP four-tuple, the original client Initial DCID, the client SCID, and server Initial SCID aliases learned after matching the server Initial to the client SCID. Separate client/server packet-number contexts are kept. Retry transitions and tuple migration are not implemented; Retry packets are reported as `retry_packets_observed_unsupported`.

Stateful CID and connection tracking is established implementation practice in complete QUIC stacks and stateful protocol analyzers, including Google's production QUICHE, ngtcp2, and Wireshark [7–9]. We do not claim CID mechanics, alias tracking, or stateful connection tracking as a new QUIC protocol invention. The project-specific contribution is the lightweight-extractor engineering/evaluation: identify and quantify the legacy current-DCID accounting blindspot, implement `InitialContextAssociator`, measure its RFC 9001 §5.2-aligned packet accounting against a pinned reference, and characterize the order boundary. The claim is limited to the two traces and tested transformations; it does not imply global novelty or full stack coverage.

JA3, JA4, JA4T, and related names refer to vendor/community constructions, not IETF-standard fingerprint algorithms. RFCs specify protocol fields; implementations select field filtering, ordering, and hashing [3]. The project therefore pins TShark 4.6.4 and treats it as a comparator, not a ground-truth oracle. See `docs/landscape.md` for the broader algorithm and visibility survey.

## 3. System and methods

### 3.1 Implementation

The C++20 core parses classic-PCAP v2.x Ethernet captures containing supported unfragmented IPv4/IPv6 UDP, recognizes QUIC v1 long headers, derives Initial keys, removes header protection, authenticates/decrypts AES-128-GCM packets, parses a supported Initial-frame subset, reassembles CRYPTO data by stream offset, and validates complete TLS ClientHello structures. The stateful mode associates Initial packets by the normalized UDP four-tuple, preserves the original client Initial DCID, learns server SCIDs as aliases, and reports stateful and DCID-keyed client accounting side by side.

The implementation does not support PCAPNG, VLAN tags, IP fragments, IPv6 extension chains, QUIC v2, Retry transitions, tuple migration/NAT rebinding, 0-RTT, every QUIC frame, or JA4 computation. The stateful associator is not a complete QUIC connection tracker.

### 3.2 Data and experimental procedure

The primary traces are the committed `captures/pcaps/quic_curl.pcap` and `captures/pcaps/quic_chromium.pcap`. The batch evaluated each trace in legacy/stateless and stateful modes over a baseline and five deterministic variants: reverse record order, fixed-seed shuffle, drop one selected Initial-CRYPTO record, drop every third selected record, and truncate a selected record. Each C++ extraction was compared to TShark's complete ClientHello output from the same PCAP variant using a byte-multiset comparison; arrival order is not used as the equality criterion. This design tests agreement with a pinned reference on identical input, not correctness against independent ground truth.

The WSL environment/build/test record and per-case outputs are under `results/track2/verification-batch-20261105-105416/`. The committed batch was executed against source commit `fa9fcdb`; its recorded environment is GCC 15.2.0, Python 3.14.4, OpenSSL 3.5.5, and TShark 4.6.4. Tool/source hashes, per-case JSON, extractor logs, TShark `jsonraw` exports, and variant captures are available in the batch directory. The separate Track 1 Docker `cn-lab` environment used TShark 4.4.19 and FoxIO binaries whose release tag and reported program versions differ (`ja4` tag v0.18.6 reports 0.18.5; `ja4-main` reports 0.18.6). These environments are not pooled as a single pin. The prior stateless baseline matrix at `results/track2/verification-batch-20261104-201936/` supplies the earlier bounded comparison.

As separate supplemental user-run WSL evidence, the user reports that filtering each original capture with `quic.long.packet_type == 0 && quic.decryption_failed` produced zero rows, including for post-switch DCIDs. Those exact filter outputs are not archived in the batch and were not independently rerun in Arena. The prototype's 16 baseline failures refer only to its own stateless per-DCID accounting. TShark/Wireshark is the stateful reference implementation and comparator in this study, not an independent oracle; its same-PCAP ClientHello byte outputs are the comparison target.

### 3.3 Supplementary evidence

L2’s passive-visibility result is the team-reported, imported one-session comparison: the same TLS 1.3 curl capture yielded 0 JA4X/JA4H records without the session key log and 5 with it (4 JA4X certificate-chain entries plus 1 JA4H). The key log is intentionally absent, so the keyed result cannot be regenerated here; it supports the visibility point for this sample, not a universal tool or protocol claim. L3 evidence combines separate single-vantage offload captures and a later user-run container/Wi-Fi pairing exercise. The paired exercise reports distinct tuples and initial sequence numbers and a checker classification of separate legs or sequence rewrite. Because there is no synchronized capture at a known physical outer boundary, these observations do not identify the intermediate mechanism. Track 1 L4/L5/L7 data remain imported or team-supplied, with their known caveats. The `LEDGER.md` and `docs/track1-evidence-audit.md` retain row-level values, provenance, and limitations.

## Quantitative results (generated from the committed batch)

Batch source: `results/track2/verification-batch-20261105-105416/`; generated by `report/build_report.py`. The batch was run in WSL against source commit `fa9fcdb8a7c4e0e2dcf2adb5b4a4f3c09c075894` and committed in the later evidence commit. Values below are read from the recorded environment, test log, JSON results, and seven-row JSON; they are not manually reconstructed from prose.

### Environment and tests

| Item | Recorded value |
|---|---|
| Source commit | fa9fcdb8a7c4e0e2dcf2adb5b4a4f3c09c075894 |
| TShark | TShark (Wireshark) 4.6.4. |
| Compiler | g++ (Ubuntu 15.2.0-16ubuntu1) 15.2.0 |
| OpenSSL | OpenSSL 3.5.5 27 Jan 2026 (Library: OpenSSL 3.5.5 27 Jan 2026) |
| Python | Python 3.14.4 |
| CTest | 1/1 (quic_core_tests) |
| pytest | 52 passed (0.51s) |

### Captured-order baseline: packet accounting and byte comparison

| Trace | 4-tuple associations | Client Initial packets | Legacy client decrypts / failures | Stateful client decrypts / failures | Stateful server packets, decrypts / failures | Context misses client / server | Alias buckets / alias packets | ClientHellos matched / reference | Misses | Extras | Multiset equal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| curl | 5 | 20 | 10/10 | 20/0 | 5, 5/0 | 0/0 | 5/10 | 5/5 | 0 | 0 | True |
| chromium | 5 | 16 | 10/6 | 16/0 | 5, 5/0 | 0/0 | 5/6 | 5/5 | 0 | 0 | True |

The SHA-256 multisets in the per-trace baseline JSON are compared without arrival-order assumptions. `Multiset equal=true` means the stateful C++ output bytes match TShark 4.6.4's ClientHello bytes for that same captured-order PCAP; this is a comparator result, not independent ground truth.

### Stateful mutation matrix

| Case | curl matched / reference | curl misses / extras | Chromium matched / reference | Chromium misses / extras |
|---|---|---|---|---|
| baseline | 5/5 | 0/0 | 5/5 | 0/0 |
| reverse-record-order | 0/5 | 5/0 | 0/5 | 5/0 |
| shuffle-record-order | 4/5 | 1/0 | 4/5 | 1/0 |
| drop-one-initial-crypto-record | 5/5 | 0/0 | 5/5 | 0/0 |
| drop-every-third-initial-crypto-record | 2/2 | 0/0 | 2/2 | 0/0 |
| truncate-middle-initial-crypto-record | 5/5 | 0/0 | 5/5 | 0/0 |

This matrix makes record-order sensitivity visible: the reversed case has zero extracted ClientHellos in each trace, and the shuffled case misses one per trace. The baseline result does not establish order-independent stateful extraction. The dropped-record/truncated cases are compared against TShark on each corresponding mutated PCAP.

### Earlier stateless comparison matrix

| Trace | Cases | Reference ClientHellos | Exact byte matches | Misses | Extras |
|---|---|---|---|---|---|
| curl | 6 | 27 | 27 | 0 | 0 |
| chromium | 6 | 27 | 27 | 0 | 0 |

The previous stateless matrix matches the TShark output for all six cases per trace (27/27 each). The every-third-drop case contains two TShark reference hellos, so 2/2 is not recovery of the five baseline hellos.

### Seven-row verifier

| Row | Artifact audit | Requested live check | Reason / note |
|---|---|---|---|
| L1_QUIC | PASS | PASS |  |
| L2_TLS_SECRETS | PASS | PASS |  |
| L3_VANTAGE_OFFLOAD | PASS | PASS |  |
| L4_PQ_MLKEM | PASS | PASS |  |
| L5_GREASE_STABILITY | PASS | PASS |  |
| L6_IPV6 | NOT_MEASURED | FAIL | EvidenceError: tcpdump produced no packet-bearing IPv6 PCAP |
| L7_ECH | PASS | PASS |  |

Overall artifact status: **INCOMPLETE**; overall live status: **FAIL**. L6's artifact status is `NOT_MEASURED` for public IPv6 egress. The optional local loopback check is a separate control and its recorded failure is not a public-egress measurement.

Primary output references: `quic-stateful/{curl,chromium}/impairment-results.json`, `quic-impairment/{curl,chromium}/impairment-results.json`, `seven-rows-live.json`, and `make-test.log`.


## 4. Discussion

The measured engineering contribution is specific: the stateless prototype derives keys from each packet’s current DCID and therefore misaccounts 10 curl plus 6 Chromium later client Initial packets in the tested traces. `InitialContextAssociator` retains the first client Initial’s ODCID and learns server SCID aliases on the normalized 4-tuple. In captured order this aligns the key context with RFC 9001 §5.2, decrypts 20/20 curl and 16/16 Chromium client Initials with zero failures, and preserves exact ClientHello byte parity against TShark 4.6.4 (5/5 per trace). This is packet-accounting correctness, not increased ClientHello recall in these captures and not a claim that CID state is new to QUIC implementations.

The mutation results qualify that conclusion. The associator is a single-pass input-record-order tracker: the first client Initial seen on a UDP four-tuple seeds the presumed original DCID, and a server SCID alias is learned only after a server Initial is observed and matched to a previously seen client SCID. In the reversed-record test, later client Initials using switched DCIDs precede the server alias announcement and the true original client Initial. The first switched DCID is therefore provisionally treated as the original context; with no packet buffering or timestamp-based reordering, the server alias is unavailable at the point of use and subsequent records miss the required context. This matches the logged reverse result of 0/5. The deterministic shuffle retains usable context for 4/5. A timestamp-aware pre-pass or bounded buffering/deferred association is a possible future design, not current behavior.

ClientHello recall remains 5/5 per trace in both the legacy stateless baseline and stateful baseline; the improvement is accounting for 10 + 6 = 16 additional client Initial packets, not discovering more ClientHellos in these captures. The user reports a frame-level audit showing that the complete ClientHellos were already wholly present in pre-switch datagrams. That audit is not yet archived, so this explanation should be labeled user-reported until its exact frame mapping is added to the evidence batch. It is capture-specific: if ClientHello bytes span post-switch datagrams, correct packet context could matter to extraction, but no such recall gain is demonstrated here.

The passive-visibility dive complements the QUIC result: the imported one-session TLS 1.3 L2 data report 0 JA4X/JA4H records without keys and 5 with keys, demonstrating the effect of secrets for that captured sample. Because the key log is not committed, this remains team-reported evidence rather than a reproducible keyed experiment. The L3 investigation is a secondary limitation study: capture point and TCP-leg identity matter, but available tuples/ISNs do not prove a proxy, a particular middlebox mechanism, or a JA4T misattribution. None of these fingerprints is a unique identity or broad privacy guarantee.

## 5. Limitations and threats to validity

- **Reference dependence:** TShark is pinned and useful as a stateful reference implementation/comparator, but the C++ and TShark outputs are compared on the same PCAPs. Agreement is not an independent truth oracle or a proof of protocol conformance. The separate zero-`quic.decryption_failed` filter result on the two original captures is user-reported supplemental WSL evidence; exact command output is not archived.
- **Trace scope:** The QUIC analysis uses two captures, one curl and one Chromium. Five associations per trace do not represent the full range of clients, networks, Retry, migration, or loss behavior. L2 is one imported TLS 1.3 session; it does not establish a universal JA4X/JA4H rule.
- **Order sensitivity:** The stateful mode's baseline result is good for captured order, while reverse/shuffle variants expose misses (0/5 and 4/5). The method processes packet records in input order, seeds its presumed original DCID from the first observed client Initial, learns server SCID aliases only after the server Initial is processed, and has no buffering/reordering pass. It cannot resolve an alias before that announcement is seen.
- **Retry and lifecycle limits:** Retry remains unsupported (`retry_packets_observed_unsupported`); migration/rebinding, QUIC v2, and complete RFC 9000/9001 behavior are also outside scope. The report does not claim full QUIC coverage.
- **ClientHello attribution:** The 5/5 pre-switch containment explanation is user-reported and not yet supported by an archived frame-by-frame mapping. Recall is unchanged in the measured baseline regardless; packet accounting, not recall, is the demonstrated gain.
- **Capture/format scope:** The parser supports classic PCAP Ethernet and a limited IPv4/IPv6 UDP path. PCAPNG, VLAN, fragments, IPv6 extension chains, QUIC v2, and other excluded cases are not validated by this report.
- **Provenance:** The 5 November run was user-executed in WSL and is now inspectable in a committed batch, not regenerated in Arena. Track 1 TLS results are imported/team-supplied.
- **L3 causality:** The captures do not establish proxy identity, TCP termination, middlebox rewriting, OS misclassification, or a JA4T/JA4TS error.
- **IPv6:** By accepted scope, public IPv6 egress is `NOT_MEASURED`. The optional local `::1` loopback control failed to produce a packet-bearing PCAP and is not a substitute for public egress.
- **Contribution status:** The project adopts the engineering/evaluation framing described above, not protocol-level CID novelty. A comprehensive prior-art review and final course-rubric confirmation are not present in this evidence set; the report does not claim to certify the grading outcome.

## 6. Future work

1. **Retry support:** validate Retry integrity and the Retry-specific Initial key-derivation transition with positive/negative vectors and captures.
2. **CID lifecycle and tuple changes:** extend association to authenticated CID updates, controlled migration/NAT rebinding, expiry, and collision handling; test both directions.
3. **Order-robust context establishment:** test buffering or delayed association for out-of-order Initial/SCID evidence, using deterministic reordered traces and explicit resource bounds. This is motivated by the current stateful reverse/shuffle results, not claimed as completed.
4. **L3 attribution:** collect synchronized captures at known client, host, and wire-facing points; separate NAT from TCP termination and test offload independently before considering any fingerprint normalizer.
5. **Broader validation:** add clients, networks, QUIC versions, Retry/migration traces, and independently validated reference paths; then review targeted prior art and the course rubric with the team.

## 7. Conclusion

For the two captured-order QUIC v1 traces, the project’s engineering/evaluation contribution is the measured stateless accounting blindspot and the first-step `InitialContextAssociator`: stateful accounting recovers 10 curl plus 6 Chromium client Initials (16 total), with zero client decrypt failures and 5/5 exact ClientHello byte matches per trace against TShark 4.6.4. It is not a new QUIC CID protocol mechanism. Reverse order (0/5) and shuffle (4/5) define the observed causal-order boundary. The second depth dive reports the L2 0-without-keys versus 5-with-keys visibility result for one TLS 1.3 sample, with the key log absent and provenance caveated. Public IPv6 remains NOT_MEASURED by accepted scope. The report presents a bounded project contribution, not full QUIC conformance, global novelty, proxy attribution, or an automatic course-rubric result.

## References

[1] J. Iyengar and M. Thomson, “Using TLS to Secure QUIC,” RFC 9001, 2021, especially §5.2. <https://www.rfc-editor.org/rfc/rfc9001.html#section-5.2>.

[2] J. Iyengar and M. Thomson, “QUIC: A UDP-Based Multiplexed and Secure Transport,” RFC 9000, 2021, especially §7.2. <https://www.rfc-editor.org/rfc/rfc9000.html#section-7.2>.

[3] FoxIO, “JA4+ Network Fingerprinting,” release v1.0.1, 2024. <https://github.com/FoxIO-LLC/ja4/releases/tag/v1.0.1>. The project treats this as an algorithm implementation reference, not a standards-track specification.

[4] “TLS, TCP, certificate, and HTTP fingerprinting landscape,” project working survey, `docs/landscape.md`. It is a comparative survey, not a systematic literature review.

[5] Wireshark Foundation, TShark 4.6.4, as recorded in `results/track2/verification-batch-20261105-105416/environment.txt`; same-PCAP reference outputs are archived with the batch.

[6] Project authors, “Stateful QUIC Initial verification batch,” user-run Ubuntu WSL, source commit `fa9fcdb`, committed as `7a2584c`, `results/track2/verification-batch-20261105-105416/`.

[7] Google, “QUICHE,” production-ready QUIC implementation repository. <https://github.com/google/quiche>.

[8] ngtcp2 project, “ngtcp2,” IETF QUIC implementation repository. <https://github.com/ngtcp2/ngtcp2>.

[9] Wireshark Foundation, “Wireshark,” network protocol analyzer source repository. <https://github.com/wireshark/wireshark>.

[10] E. Rescorla, “The Transport Layer Security (TLS) Protocol Version 1.3,” RFC 8446, especially §4.4.2. <https://www.rfc-editor.org/rfc/rfc8446.html#section-4.4.2>.
