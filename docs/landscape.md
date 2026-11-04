# Fingerprinting landscape (working scaffold)

**Status:** Preliminary landscape scaffold, not a completed literature review or novelty claim. The sources below are primary implementation/specification starting points. Before submission, pin versions/commits, verify each construction against its source, add relevant papers and prior art, and record who reviewed them.

## Fingerprint families and observation surfaces

| Family / tool | Main protocol and observation | Typical output / role | Capture-point and interpretation caveats | Project relevance |
|---|---|---|---|---|
| **JA3 / JA3S** | TLS ClientHello / ServerHello fields | Compact client / server TLS fingerprint | Requires the relevant handshake fields to be visible or decrypted; a terminating intermediary presents its own TLS handshake. Treat an output as describing the observed TLS endpoint, not necessarily the ultimate application peer. | Imported Track 1 baseline; compare only with pinned JA3 implementation and documented field handling. [Salesforce JA3](https://github.com/salesforce/ja3) |
| **JA4 / JA4S (JA4+)** | TLS handshake and related protocol-specific inputs; the implementation also reports QUIC-form fingerprints in the imported samples | Versioned, structured client / server fingerprint families | Exact fields, ordering, normalization, and supported protocol versions are implementation/version dependent. Preserve raw inputs and pin a release/commit; do not hand-infer a JA4 string. | Existing TShark/FoxIO comparisons and the QUIC required depth dive. [FoxIO JA4](https://github.com/FoxIO-LLC/ja4), [v1.0.1 release](https://github.com/FoxIO-LLC/ja4/releases/tag/v1.0.1) |
| **JA4T / JA4TS** | TCP SYN / SYN-ACK characteristics, including TCP options | Client-side / server-side TCP fingerprint, often used for stack attribution | Describes the TCP endpoint visible at the capture point. NAT may translate tuples without terminating TCP; a terminating proxy creates separate legs; TTL and advertised MSS alone do not prove identity or proxying. Capture vantage must be explicit. | Provisional L3 question. Current checker reports raw profiles and conservative paired-stream comparisons; it does not calculate JA4T/JA4TS. Pin the actual construction before comparing results. See `docs/l3-contribution-plan.md`. |
| **p0f** | Passive TCP/IP packet characteristics, especially connection-opening packets | Passive OS / network-stack fingerprint inference | Signature database and packet vantage matter; NAT, proxies, OS configuration, and middleboxes can change or obscure observed characteristics. It is an adjacent prior-art baseline, not interchangeable with JA4T. | Include in prior-art review for passive TCP attribution. [p0f source](https://github.com/p0f/p0f) |
| **Wireshark / TShark** | Protocol dissection and field export over captured traffic | Packet fields, reassembly, diagnostic reference; not itself one fingerprint algorithm | Dissector support, capture completeness, field semantics, and version affect output. A reference parser is not automatically ground truth. Save version, command, raw export, and input hash. | Used as the QUIC byte reference and TCP SYN/SYN-ACK extractor. [Wireshark source](https://github.com/wireshark/wireshark) |
| **QUIC Initial / TLS ClientHello extraction** | QUIC v1 Initial packets, protected with Initial keys, carrying TLS handshake CRYPTO frames | Reassembled ClientHello and derived TLS fingerprints | Initial secrets use the client's first Initial DCID (with Retry-specific handling); later connection-ID changes do not replace that key-schedule input. Packet direction and connection context are essential. See RFC 9000/9001. | Required depth dive; current C++ core is a correctness baseline, not the contribution claim for tested conditions. [RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html), [RFC 9001](https://www.rfc-editor.org/rfc/rfc9001.html) |

## Project-specific evidence snapshot

| Question | Evidence currently in the repository | Interpretation and open gap |
|---|---|---|
| Can the QUIC extractor recover these two clean baselines? | Committed PCAPs and comparison record; user reports 5/5 byte-identical ClientHellos per capture against TShark. | User-reported exact-byte comparison; raw TShark arrays and comparison script are still missing. This is not broad protocol coverage. |
| Why do five extra per-DCID buckets fail decryption? | Reproducible header inventory: five UDP flows per capture; each first observed client Initial DCID is 8 bytes, and a later client Initial DCID equals the 20-byte SCID from the server Initial. | Current CLI groups by each packet DCID and derives using it. This is the expected post-switch CID/key-context limitation, not five server-direction attempts and not a missed-ClientHello result for these traces. See `docs/quic/implementation-status.md`. |
| Is WSL `eth0` a valid outer capture point for the reported Docker Desktop probe? | User reports the container handshake was absent from WSL `eth0`; a user-transcribed summary is in `results/track2/l3-paired-probe-c28a486.md`. | Reject WSL `eth0` as the outer point for that probe. The reported Docker Desktop utility-VM explanation is still a hypothesis; synchronized Windows-side packet evidence is needed. |
| Do the imported offload PCAPs prove a proxy? | User-reported TShark checker run shows repeatable intra-capture SYN/SYN-ACK option asymmetry. | No. The two captures are separate runs, not paired points. The controlled probe reported a different peer MSS (1460). Need repeated captures bracketing a known boundary and separate TSO/GSO. |

## Comparison matrix to complete

For each implementation, record repository/release/commit, source citation, supported protocol/version, exact observed fields, direction (client/server), required capture point, visibility/decryption requirements, normalization, database/version, and known middlebox effects. Add a small reproducible reference run and raw input/output hashes. Do not compare fingerprint strings across tools until field construction and output version are aligned.

| Workstream | Candidate references | Immediate review task | Status |
|---|---|---|---|
| TLS client/server fingerprints | JA3, JA4; RFC TLS definitions | Verify exact field inclusion, GREASE handling, ordering, and versioned implementations used in Track 1 | Partial; implementation provenance remains incomplete |
| QUIC/TLS handshake visibility | RFC 9000, RFC 9001; TShark QUIC/TLS dissector; FoxIO JA4 | Compare Initial-secret and reassembly behavior, including Retry and switched DCIDs | Header-level DCID explanation recorded; no new recovery contribution demonstrated |
| TCP stack/passive OS fingerprints | JA4T/JA4TS, p0f, packet-analysis literature | Find prior work on capture-vantage attribution, NAT versus termination, Docker Desktop/VM networking, and fingerprint stability | Open; no novelty claim |
| Capture and segmentation artifacts | TShark/Wireshark, tcpdump, offload documentation | Separate capture point, checksum/segmentation offload, and real TCP-leg changes | Open; need simultaneous boundary evidence |

## Submission gate

This page is a starting index, not a claim that a comprehensive literature survey has been completed. The L3 direction is provisional. No original contribution should be asserted until paired raw evidence is committed, the relevant prior art is reviewed, the course rubric is checked by the team, and limitations/negative results are included.
