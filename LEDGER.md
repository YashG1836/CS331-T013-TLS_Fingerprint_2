# Limitation ledger — Track 1 evidence and Track 2 candidates

Track 1 has 15 imported capture attempts. They are team-supplied, not rerun here, and remain provisional. Fourteen contain packets; the IPv6 file is empty. FoxIO's Rust CLI uses TShark, so matching JA4 values are not independent packet-decoder agreement. The earlier aioquic QUIC v1 capture remains a separate provisional baseline. Full cross-checks and inconsistencies are in [`docs/track1-evidence-audit.md`](docs/track1-evidence-audit.md).

| ID | Limitation question | Imported evidence snapshot | Status / next validation |
|---|---|---|---|
| L1 | Do reference tools expose QUIC v1 ClientHellos and fingerprints? | `quic_chromium` and `quic_curl`: supplied summary reports 5/5 hellos each; Chromium reports up to 21 CRYPTO fragments. TShark/FoxIO JA4 outputs match. | No reference-tool gap shown in these samples. Not a test of our C++ core. Next compare both captures against flow-aware C++ recovery byte-for-byte. |
| L2 | Which certificate/HTTP fingerprints require TLS secrets? | `tls_keylog_curl`: supplied summary reports JA4X/JA4H count 0 without keys and 5 with keys. | Provisional single TLS 1.3 sample. Key log intentionally absent, so keyed arm cannot be regenerated from repository. |
| L3 | How do capture point and offload affect transport observations? | Supplied aggregate reports `pieces_max` 1/2 with TSO/GSO on/off; T3 narrative reports large frames and SYN-ACK MSS 65495 from a Docker proxy. | Provisional and internally mismatched: narrative frame counts/sizes do not match saved aggregate fields; raw JSON lacks SYN values. Rerun targeted queries at a documented vantage. |
| L4 | How do PQ versus classic key-share settings affect ClientHello size and fingerprint? | `tls_pq_on/off`: summary reports lengths 1511/508 bytes and selected groups 4588/29; JA4 differs with extension-set changes. | Provisional, one client and environment. Verify exact tool outputs and avoid attributing JA4 change directly to the negotiated group. |
| L5 | How stable are fingerprints across repeated connections and related clients? | `tls_chromium_repeat`: 50 reported hellos, 50 distinct JA3s, 15 released-tool JA4s, 1 from FoxIO `ja4-main` commit `c6469a7…`; curl/Python report one JA4 each in 10 hellos. | Promising release-vs-unreleased observation; reproduce the tool/source builds and verify GREASE cause. Existing upstream fix means the result is not itself a novel contribution. |
| L6 | Does IPv6 change TLS/TCP fingerprint observations? | `tls_ipv6.pcap` is 24 bytes and has zero packet records; source summary's empty-set equality has been corrected to not-comparable. | Not measured. Repeat on a network with IPv6 and validate packets before analysis. |
| L7 | How do ECH and encrypted DNS affect name attribution? | Saved ECH-off/on page outputs report `sni=plaintext` / `sni=encrypted`. The ECH+DoH page output is empty despite 12 summary ClientHellos in the pcap. | ECH off/on is a team-reported observation; intended DoH arm incomplete. Separate target traffic from Chromium background connections and rerun. |

A TLS 1.3 certificate-compression/abridging scenario remains a watch item, not one of the seven measured rows. Do not label simulations as observed traffic.

## Candidate original contribution / improvement

| Candidate | Evidence basis | Assessment |
|---|---|---|
| Chromium GREASE-stability issue in released JA4 | T5 reports 15 released-tool outputs versus one from a specified unreleased FoxIO commit. | Already fixed upstream according to the supplied source comparison; useful regression measurement, not a new implementation claim. Verify provenance/root cause. |
| JA4T/JA4TS plus capture-vantage/MSS sanity diagnostics | T3 suggests the observed SYN-ACK may be from Docker Desktop's proxy, not the remote server. | Interesting, but raw SYN rows and narrative/aggregate frame metrics are missing or inconsistent. Reproduce first; check existing JA4T/Zeek implementations and originality. |
| **Flow-aware QUIC Initial PCAP recovery with explicit completeness/loss diagnostics** | Required Track 2 core; Chromium capture reports up to 21 CRYPTO fragments. The new bounded classic-PCAP reader and first DCID-scoped CLI path recover five ClientHellos from each imported QUIC capture, with length/framing but not byte-exact independent reference checks. | **Candidate, not yet an originality claim.** Improve flow modeling and unsupported-case diagnostics; measure recovery under controlled order/loss/truncation variants, obtain a TShark raw-byte reference, and check prior art/course rubric before claiming novelty. |
| ECH/DNS name-visibility table | T7 page outputs show the outer name behavior in two conditions. | Useful reporting, but likely an analysis rather than a standalone technical contribution. The DoH arm still needs evidence. |

Do not select a final original contribution until evidence gaps, related work, and the course rubric have been reviewed with the team.
