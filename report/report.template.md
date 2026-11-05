# Where Protocol Fingerprints Stop: Stateful QUIC Initial Accounting and Capture-Vantage Limits

**CS331 Phase 2 — formal report draft**

**Authors:** [insert approved team member names]

**Date:** 5 November 2026
**Status:** Working draft for team/rubric review; not an approved final contribution claim.

> **Evidence note.** Quantitative tables below are generated from the committed WSL batch by `python3 report/build_report.py`. The 5 November execution was run in Ubuntu WSL against source commit `fa9fcdb` and committed with its artifacts in `7a2584c`. It is inspectable here but was not independently regenerated in Arena. Track 1 TLS experiments remain imported/team-supplied. TShark 4.6.4 is the comparison reference on the same PCAPs—not independent ground truth.

## Abstract

Passive protocol fingerprints describe fields visible at a particular network capture point; they do not, by themselves, identify a user, application, or ultimate server behind an intermediary. This project evaluates that boundary through a C++20 QUIC v1 Initial-to-ClientHello extractor and a secondary review of TCP/TLS fingerprint experiments. A stateful Initial-context mode associates packets on a direction-normalized UDP four-tuple, retains the original client Initial Destination Connection ID (DCID), and learns server Initial Source Connection IDs (SCIDs). Against the prototype's legacy stateless accounting, the captured-order stateful mode recovers accounting for 10 additional curl and 6 additional Chromium client Initial packets (10/20 to 20/20 and 10/16 to 16/16); complete ClientHello byte parity remains 5/5 per trace in both modes. Reversing record order yields 0/5 matches and shuffling 4/5, exposing a single-pass ordering limitation. CID mechanics and stateful tracking are not claimed as globally novel: the project evaluates a minimal stateless-to-stateful transition in lightweight passive streaming fingerprinting. The result is a bounded engineering/evaluation proposal, not full QUIC conformance or an established novelty finding. The L3 evidence is consistent with distinct TCP legs at two observation points but does not establish proxy termination or fingerprint misattribution. Other TLS rows are imported evidence with explicit missing arms. Public IPv6 egress remains unmeasured; the local loopback capture attempt did not produce a packet-bearing PCAP.

**Keywords:** QUIC Initial, connection ID, ClientHello, protocol fingerprint, capture vantage, TShark, evidence provenance.

## 1. Introduction

Transport and TLS fingerprints are summaries of observable protocol fields. Their meaning depends on which leg is captured, which messages are visible, and how the tool normalizes those fields. A SYN profile describes the TCP endpoint visible at that capture point. A ClientHello fingerprint describes the ClientHello visible on that TLS leg. Neither necessarily identifies the intended remote application endpoint when a TCP/TLS-terminating intermediary exists; conversely, one unusual MSS, TTL, or fingerprint is not proof that such an intermediary exists [4].

QUIC adds a specific packet-accounting question. A QUIC v1 Initial's packet protection can be derived from public version and connection-ID inputs. RFC 9001 §5.2 defines the Initial key schedule around the original client Initial DCID (with a Retry-specific transition) [1]. A later client Initial can use a server-provided SCID as its current DCID without changing the original Initial secret. The project's earlier C++ prototype derived keys independently from each packet's current DCID, creating decrypt-failure buckets for such later client packets even though its complete ClientHello outputs matched TShark in the original traces.

This report focuses on the narrow stateful accounting correction and its verified scope. L3 capture-vantage analysis is secondary. The project does not claim a new fingerprint standard, a complete QUIC implementation, a demonstrated proxy detector, or a course-rubric-approved original contribution.

### Research questions

1. Does retaining QUIC v1 Initial context across a stable UDP four-tuple eliminate the prototype's post-switch client Initial decrypt failures in the captured-order curl and Chromium traces?
2. For those traces, do the stateful ClientHello bytes match TShark 4.6.4, and what does the deterministic record-order matrix reveal about statefulness limits?
3. What do the supporting TCP/TLS fingerprint experiments establish—and, importantly, what do their capture points and provenance not establish?

## 2. Background

QUIC connection IDs support routing and connection continuity, but the Initial key derivation rule is tied to the original Initial DCID rather than an arbitrary later packet's DCID [1, 2]. Therefore, a packet-level extractor needs state to associate packets and direction. This project implements a deliberately bounded state model: a direction-normalized IPv4/IPv6 UDP four-tuple, the original client Initial DCID, the client SCID, and server Initial SCID aliases learned after matching the server Initial to the client SCID. Separate client/server packet-number contexts are kept. Retry transitions and tuple migration are not implemented; Retry packets are reported as `retry_packets_observed_unsupported`.

Stateful CID and connection tracking is established implementation practice in complete QUIC stacks and stateful protocol analyzers, including Google's production QUICHE, ngtcp2, and Wireshark [7–9]. We do not claim CID mechanics, alias tracking, or stateful connection tracking as a globally novel discovery. The narrower project scope is to evaluate a minimal stateless-to-stateful transition in a lightweight passive streaming fingerprinter: measure packet-accounting recovery on two traces, preserve the existing ClientHello byte comparison, and expose the order boundary of learning state in a single pass. This is a proposed engineering/evaluation contribution, not proof of novelty; a targeted prior-art review and course-rubric/team review remain necessary.

JA3, JA4, JA4T, and related names refer to vendor/community constructions, not IETF-standard fingerprint algorithms. RFCs specify protocol fields; implementations select field filtering, ordering, and hashing [3]. The project therefore pins TShark 4.6.4 and treats it as a comparator, not a ground-truth oracle. See `docs/landscape.md` for the broader algorithm and visibility survey.

## 3. System and methods

### 3.1 Implementation

The C++20 core parses classic-PCAP v2.x Ethernet captures containing supported unfragmented IPv4/IPv6 UDP, recognizes QUIC v1 long headers, derives Initial keys, removes header protection, authenticates/decrypts AES-128-GCM packets, parses a supported Initial-frame subset, reassembles CRYPTO data by stream offset, and validates complete TLS ClientHello structures. The stateful mode associates Initial packets by the normalized UDP four-tuple, preserves the original client Initial DCID, learns server SCIDs as aliases, and reports stateful and DCID-keyed client accounting side by side.

The implementation does not support PCAPNG, VLAN tags, IP fragments, IPv6 extension chains, QUIC v2, Retry transitions, tuple migration/NAT rebinding, 0-RTT, every QUIC frame, or JA4 computation. The stateful associator is not a complete QUIC connection tracker.

### 3.2 Data and experimental procedure

The primary traces are the committed `captures/pcaps/quic_curl.pcap` and `captures/pcaps/quic_chromium.pcap`. The batch evaluated each trace in legacy/stateless and stateful modes over a baseline and five deterministic variants: reverse record order, fixed-seed shuffle, drop one selected Initial-CRYPTO record, drop every third selected record, and truncate a selected record. Each C++ extraction was compared to TShark's complete ClientHello output from the same PCAP variant using a byte-multiset comparison; arrival order is not used as the equality criterion. This design tests agreement with a pinned reference on identical input, not correctness against independent ground truth.

The WSL environment/build/test record and per-case outputs are under `results/track2/verification-batch-20261105-105416/`. The committed batch was executed against source commit `fa9fcdb`. Tool/source hashes, per-case JSON, extractor logs, TShark `jsonraw` exports, and variant captures are available in the batch directory. The prior stateless baseline matrix at `results/track2/verification-batch-20261104-201936/` supplies the earlier bounded comparison.

As separate supplemental user-run WSL evidence, the user reports that filtering each original capture with `quic.long.packet_type == 0 && quic.decryption_failed` produced zero rows, including for post-switch DCIDs. Those exact filter outputs are not archived in the batch and were not independently rerun in Arena. The prototype's 16 baseline failures refer only to its own stateless per-DCID accounting. TShark/Wireshark is the stateful reference implementation and comparator in this study, not an independent oracle; its same-PCAP ClientHello byte outputs are the comparison target.

### 3.3 Supplementary evidence

L3 evidence combines separate single-vantage offload captures and a later user-run container/Wi-Fi pairing exercise. The paired exercise reports distinct tuples and initial sequence numbers and a checker classification of separate legs or sequence rewrite. Because there is no synchronized capture at a known physical outer boundary, these observations do not identify the intermediate mechanism. Track 1 L2/L4/L5/L7 data remain imported or team-supplied; missing secrets and incomplete page arms are not reconstructed. The `LEDGER.md` and `docs/track1-evidence-audit.md` retain row-level values, provenance, and caveats.

<!-- BEGIN GENERATED RESULTS -->
<!-- END GENERATED RESULTS -->

## 4. Discussion

The captured-order baseline supports a narrow conclusion: the prototype's stateful Initial context removes the observed post-switch DCID client decrypt failures for the two fixed-tuple traces, and the resulting complete ClientHello byte multisets match TShark 4.6.4 on the same captured-order PCAPs. This corrects the prototype's internal packet accounting for the tested case in a manner aligned with RFC 9001's Initial key context. It does not improve ClientHello recall over the earlier baseline, which already matched the complete reference outputs.

The mutation results qualify that conclusion. The associator is a single-pass input-record-order tracker: the first client Initial seen on a UDP four-tuple seeds the presumed original DCID, and a server SCID alias is learned only after a server Initial is observed and matched to a previously seen client SCID. In the reversed-record test, later client Initials using switched DCIDs precede the server alias announcement and the true original client Initial. The first switched DCID is therefore provisionally treated as the original context; with no packet buffering or timestamp-based reordering, the server alias is unavailable at the point of use and subsequent records miss the required context. This matches the logged reverse result of 0/5. The deterministic shuffle retains usable context for 4/5. A timestamp-aware pre-pass or bounded buffering/deferred association is a possible future design, not current behavior.

ClientHello recall remains 5/5 per trace in both the legacy stateless baseline and stateful baseline; the improvement is accounting for 10 + 6 = 16 additional client Initial packets, not discovering more ClientHellos in these captures. The user reports a frame-level audit showing that the complete ClientHellos were already wholly present in pre-switch datagrams. That audit is not yet archived, so this explanation should be labeled user-reported until its exact frame mapping is added to the evidence batch. It is capture-specific: if ClientHello bytes span post-switch datagrams, correct packet context could matter to extraction, but no such recall gain is demonstrated here.

The L3 investigation is useful as a limitation study: capture point and TCP-leg identity matter when interpreting a fingerprint. The available evidence shows different tuples/ISNs across selected views, but does not prove that a proxy terminated a flow, that a specific middlebox rewrote a packet, or that JA4T misidentified an operating system. Imported TLS observations similarly support only their narrow measured samples; they do not establish broad fingerprint uniqueness or privacy guarantees.

## 5. Limitations and threats to validity

- **Reference dependence:** TShark is pinned and useful as a stateful reference implementation/comparator, but the C++ and TShark outputs are compared on the same PCAPs. Agreement is not an independent truth oracle or a proof of protocol conformance. The separate zero-`quic.decryption_failed` filter result on the two original captures is user-reported supplemental WSL evidence; exact command output is not archived.
- **Trace scope:** The QUIC analysis uses two captures, one curl and one Chromium. Five associations per trace do not represent the full range of clients, networks, Retry, migration, or loss behavior.
- **Order sensitivity:** The stateful mode's baseline result is good for captured order, while reverse/shuffle variants expose misses (0/5 and 4/5). The method processes packet records in input order, seeds its presumed original DCID from the first observed client Initial, learns server SCID aliases only after the server Initial is processed, and has no buffering/reordering pass. It cannot resolve an alias before that announcement is seen.
- **Retry and lifecycle limits:** Retry remains unsupported (`retry_packets_observed_unsupported`); migration/rebinding, QUIC v2, and complete RFC 9000/9001 behavior are also outside scope. The report does not claim full QUIC coverage.
- **ClientHello attribution:** The 5/5 pre-switch containment explanation is user-reported and not yet supported by an archived frame-by-frame mapping. Recall is unchanged in the measured baseline regardless; packet accounting, not recall, is the demonstrated gain.
- **Capture/format scope:** The parser supports classic PCAP Ethernet and a limited IPv4/IPv6 UDP path. PCAPNG, VLAN, fragments, IPv6 extension chains, QUIC v2, and other excluded cases are not validated by this report.
- **Provenance:** The 5 November run was user-executed in WSL and is now inspectable in a committed batch, not regenerated in Arena. Track 1 TLS results are imported/team-supplied.
- **L3 causality:** The captures do not establish proxy identity, TCP termination, middlebox rewriting, OS misclassification, or a JA4T/JA4TS error.
- **IPv6:** The committed IPv6 PCAP is empty. Public IPv6 egress is `NOT_MEASURED`. The batch's local `::1` attempt failed to produce a packet-bearing PCAP; loopback is not a substitute for public egress.
- **Contribution status:** No standalone grading rubric, team-approved claim, or completed systematic prior-art review is present in the evidence set. This report is a draft, not a certification of course or novelty requirements.

## 6. Future work

1. **Retry support:** validate Retry integrity and the Retry-specific Initial key-derivation transition with positive/negative vectors and captures.
2. **CID lifecycle and tuple changes:** extend association to authenticated CID updates, controlled migration/NAT rebinding, expiry, and collision handling; test both directions.
3. **Order-robust context establishment:** test buffering or delayed association for out-of-order Initial/SCID evidence, using deterministic reordered traces and explicit resource bounds. This is motivated by the current stateful reverse/shuffle results, not claimed as completed.
4. **L3 attribution:** collect synchronized captures at known client, host, and wire-facing points; separate NAT from TCP termination and test offload independently before considering any fingerprint normalizer.
5. **Broader validation:** add clients, networks, QUIC versions, Retry/migration traces, and independently validated reference paths; then review targeted prior art and the course rubric with the team.

## 7. Conclusion

For the two captured-order QUIC v1 traces, stateful Initial context association aligns the prototype's packet-level key use with the original client Initial DCID and recovers the 10 curl plus 6 Chromium client Initials (16 total) missed by the prototype's legacy stateless accounting. Complete ClientHello byte parity remains 5/5 per trace against TShark 4.6.4, so the measured gain is packet accounting, not increased baseline recall. Synthetic record-order changes expose an important limitation, and the auxiliary L3 evidence does not prove proxy attribution. Public IPv6 egress remains unmeasured. The defensible outcome is a bounded engineering/evaluation result with explicit limits—not a claim of full QUIC compliance, globally novel CID tracking, a novel fingerprint detector, or final team/rubric approval.

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
