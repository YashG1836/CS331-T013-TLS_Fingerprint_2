# Presentation status — slide-ready draft material

**Status:** Evidence-backed slide outline and tables are prepared; no final deck/contribution claim exists yet. Keep provenance badges visible: `WSL BATCH — user-run, artifacts inspected` vs `TRACK 1 — imported/team-supplied`. The WSL run was not independently regenerated in Arena. TShark is the comparison reference on the same mutated PCAP, not independent ground truth.

## Recommended presentation narrative

**Title:** *Where Protocol Fingerprints Stop: QUIC Extraction and Capture-Vantage Limits*

**Takeaway:** The C++20 QUIC extractor matches TShark in the tested two-trace impairment matrix, so QUIC recovery is not a supported novelty claim. A TCP capture-vantage attribution question remains for paired testing; repeated MSS/window/TTL observations alone do not establish a proxy or a novel JA4T detector.

## Slide outline

| Slide | Content | Evidence label / speaker note |
|---|---|---|
| 1. Research question | When do passive TLS/TCP fingerprints describe the observed network leg rather than the intended application endpoint? | Frame the work as a project investigation; do not announce a final original contribution. |
| 2. Fingerprint visibility | One strip: TCP SYN → TLS ClientHello/ServerHello → certificate → HTTP request; show ECH, TLS 1.3 encryption, QUIC Initial boundary. | Fingerprint algorithms are vendor/community-defined, not RFC-defined. Cite `docs/landscape.md`. |
| 3. System architecture | C++20 QUIC v1 Initial path plus Python experiment/reference layer. | Current bounded implementation; JA4 generation and full connection tracking are out of scope. |
| 4. QUIC validation | 2 captures × 6 variants; 54/54 reference outputs matched, zero misses/extras. | `WSL BATCH — user-run, artifacts inspected`; TShark reference; bounded coverage. |
| 5. CID context | Later client Initial uses switched DCID matching server Initial SCID; Initial secret still uses original client Initial DCID (RFC 9001 §5.2). | Five extra per-DCID failure buckets per trace are not server-direction attempts or demonstrated missed hellos. |
| 6. L3 observation | Table with repeated SYN/SYN-ACK profiles; display two single-vantage captures as separate, not as a paired experiment. | Say “candidate question”; 65495 is not proxy proof. Separate user-reported WSL-eth0-missing probe requires Windows-side capture. |
| 7. Imported TLS observations | Compact T4/T5/T7 table: PQ size/group, Chromium JA3/JA4 variation, ECH outer name. | `TRACK 1 — imported/team-supplied`; include per-arm/sample counts and open gaps. |
| 8. Limits and next experiment | Paired captures, NAT vs termination, TSO/GSO isolation, prior-art/rubric gate. | No final contribution selected until evidence and team review. |

## Slide-ready metrics

| Area | Headline metric | Caption that must remain visible |
|---|---|---|
| WSL build/test | CTest **1/1**; pytest **39/39**; manifest **16** records (**15** packet-bearing, **1** empty). | WSL batch; GCC 15.2.0, OpenSSL 3.5.5, TShark 4.6.4; user-run/imported. |
| QUIC impairment | **54/54** exact-byte multiset matches; **0** misses, **0** extras; 12 case/client comparisons. | TShark reference on same variant PCAP; every-third-drop arm is 2/2 per trace, not five original recoveries. |
| QUIC CID inventory | **5** flows per trace; each later client Initial DCID matches server Initial SCID. | Header inventory; post-switch client packets, not server-direction decrypt attempts. |
| L3 offload captures | **3** complete SYN/SYN-ACK pairs in each of **2** separate PCAPs. Client `1460/10/64240/64`; peer `65495/7/65408/63`; frame length **74 B**. | Single-vantage, separate traces; same-capture option asymmetry is not proxy evidence. |
| L4 PQ/classic | **5** hellos per arm; TShark lengths **1511 vs 508**; selected groups **4588 vs 29**. | Imported curl experiment; one client/environment; JA4 differs with extension features. |
| L5 repeat | Chromium: **50** hellos, **50** JA3, **15** released-path JA4; **15** GREASE-pattern first signature-algorithm values. | Imported raw output; `ja4-main=1` is reported, but raw per-capture output is absent. |
| L7 ECH/DoH | ECH off/on: **5** hello rows each; target outer SNI **2** off rows, public name `cloudflare-ech.com` **2** on rows. DoH arm **12** outer `cloudflare-dns.com` rows. | Team-supplied page outputs; target DoH page output empty and arm incomplete. |

## Architecture diagrams

### QUIC extraction and reference comparison

```text
PCAP → link/IP/UDP → QUIC v1 Initial → derive keys from original client Initial DCID
                                      → authenticate/decrypt → Initial frames
                                      → CRYPTO offset reassembly → validate ClientHello
                                                               → compare bytes to TShark
```

```text
C++20 core: packet/crypto/frame/reassembly/TLS parsing
                  │ extracted ClientHello bytes
                  ▼
Python harness: fixed-seed mutation + manifests + per-case evaluation
                  │ same PCAP variant
          ┌───────┴────────┐
          ▼                ▼
       C++ CLI          TShark reference
          └──── byte-multiset comparison ────┘
```

Use the note “comparison reference, not independent ground truth.” The current CLI has bounded classic-PCAP/QUIC v1 client-Initial support and no JA4 computation.

### L3 capture-vantage experiment (proposed, not completed)

```text
Container/client ── TCP leg A ── [bridge / VM / host boundary] ── TCP leg B? ── remote
       │                                  │                                 │
   capture A                         capture B required                endpoint
```

Pair records by the controlled request and timing, then compare SYN/SYN-ACK tuple, sequence, options, and timestamps. NAT and TCP termination are different hypotheses; a single MSS, TTL, or capture cannot distinguish them. Keep offload toggles separate.

## Wording guardrails

- Say **“matches TShark in the tested matrix”**, not “proves QUIC correctness.”
- Say **“observed MSS 65495 in two single-vantage captures”**, not “proxy-generated/impossible MSS.”
- Say **“candidate to test”**, not “new proxy detector” or “JA4T is wrong.”
- Say **“ECH page observations; DoH arm incomplete”**, not “ECH+DoH hides the site.”
- Attribute every imported Track 1 table to the supplied capture/report set; the team outputs were not fully rerun in Arena.
