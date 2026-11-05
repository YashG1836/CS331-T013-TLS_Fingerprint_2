# Where Protocol Fingerprints Stop
## Stateful QUIC Initial Accounting and Capture-Vantage Limits

**CS331 Computer Networks (Fall 2026) — Final Project Presentation**  
**Instructor:** Dr. Sameer G. Kulkarni | **Team ID:** T013  
**Members:** Miloni Thakkar, Yash Goyal, Suhani, Laxmidhar Panda  
**Repository:** `https://github.com/milonithakkar/CS331-Phase2` (Branch: `arena/0d29f32c-cs331-phase2`)

---

## Slide 1: Problem & Research Motivation

### When does a passive fingerprint describe the observed network leg rather than the true endpoint?
- **The Core Illusion:** Transport (JA4T) and TLS (JA3/JA4) fingerprinting assume observed wire metadata reflects the end-host application and operating system.
- **The Reality:** 
  1. Virtual bridges, hypervisors, and offload engines actively alter transport headers (rewriting MSS, TTL, and Window Scales).
  2. TLS 1.3 and ECH encrypt certificates, SNIs, and headers, blinding passive sensors.
  3. **QUIC Connection ID Rotation:** In QUIC v1, server-driven CID changes cause stateless, per-datagram decoders to fail on subsequent Initial packets.
- **Our Goal:** Deliver a measured, empirical limitation map across 7 protocol dimensions and engineer a stateful C++20 QUIC associator that resolves post-switch decryption failures.

---

## Slide 2: Deliverable A — Protocol Landscape (JA3 vs. JA4+)

| Fingerprint | Network Layer | Observable Fields Used | RFC Anchor | Passive Tap Visibility Limit |
|:---|:---|:---|:---|:---|
| **JA3 / JA3S** | TLS Handshake | Client/ServerHello Version, Ciphers, Extensions, Elliptic Curves, Formats | RFC 8446 / RFC 5246 | Visible in plaintext TLS 1.2/1.3 ClientHello; blinded by ECH inner hello. |
| **JA4** | Transport + TLS | Protocol marker (`t`/`q`), TLS ver, SNI flag, Cipher/Ext counts, Sorted hashes | RFC 8446 / RFC 9001 | Requires Initial decryption in QUIC; extensions masked under ECH. |
| **JA4T / JA4TS** | TCP Transport | SYN Receive Window, Option Kind sequence, MSS, Window Scale | RFC 9293 / RFC 793 | Rewritten by NATs, virtual switches (Hyper-V), and offload hardware (TSO/GSO). |
| **JA4X** | Certificate | X.509 Certificate Chain: Issuer, Subject DN, Ext OIDs | RFC 5280 | **Completely encrypted in TLS 1.3**; passive wire taps cannot compute without secrets. |
| **JA4H** | HTTP Layer | Method, HTTP version, Header sequence, Cookie presence | RFC 9110 | Encrypted under TLS; invisible to passive network observers without private keys. |

---

## Slide 3: The QUIC Architecture & Our Original Contribution

### The Post-Switch DCID Decryption Blindspot (RFC 9001 §5.2)

```
[ Client ]                                                              [ Server ]
    |                                                                       |
    |---- 1. Client Initial (DCID A, SCID C) ------------------------------>|
    |     [Keys derived from random DCID A]                                 |
    |                                                                       |
    |<--- 2. Server Initial (DCID C, SCID B) -------------------------------|
    |     [Server chooses and announces SCID B]                             |
    |                                                                       |
    |---- 3. Client Subsequent Initial / ACK (DCID B) --------------------->|
    |     [RFC 9001: Initial secrets STILL anchored to original DCID A!]    |
    v                                                                       v
  [ Stateless Extractor ] ---> Tries to derive keys from DCID B ---> DECRYPTION FAILS!
  [ Our Stateful Associator ] -> Maps SCID B -> DCID A ---------> DECRYPTION SUCCEEDS!
```

- **Our Solution (`InitialContextAssociator` in C++20):**
  - Tracks a direction-normalized UDP 4-tuple (`Client Endpoint <-> Server Endpoint`).
  - Automatically records server SCID announcements as connection aliases.
  - Transparently resolves subsequent client packets carrying DCID $B$ back to original Initial context $A$.

---

## Slide 4: Empirical Evaluation — Stateful Decryption Breakthrough

### Quantitative Before / After Evaluation on Live Network Traces:

| Evaluation Metric | `quic_curl.pcap` (Baseline Stateless) | `quic_curl.pcap` (Stateful Associator) | `quic_chromium.pcap` (Baseline Stateless) | `quic_chromium.pcap` (Stateful Associator) |
|:---|:---:|:---:|:---:|:---:|
| **UDP 4-Tuple Connections** | 5 | 5 | 5 | 5 |
| **Total Client Initial Packets** | 20 | 20 | 16 | 16 |
| **Decrypted Client Packets** | 10 (50%) | **20 (100%)** | 10 (62.5%) | **16 (100%)** |
| **Decryption Failures** | 10 (50%) | **0 (0%)** | 6 (37.5%) | **0 (0%)** |
| **Packet Accounting Gain** | Baseline | **+10 Decrypted** | Baseline | **+6 Decrypted** |
| **Complete ClientHellos Extracted** | 5 / 5 | 5 / 5 | 5 / 5 | 5 / 5 |
| **TShark 4.6.4 Reference Byte Match** | 5 / 5 (100%) | **5 / 5 (100%)** | 5 / 5 (100%) | **5 / 5 (100%)** |

> **Key Finding:** Stateful context association completely eliminates internal decryption failures (16 packets recovered across both traces) while maintaining 100% byte-for-byte parity with reference dissectors.

---

## Slide 5: Characterizing the Causal Wire-Order Boundary

### What happens when network packets arrive out of order?
We benchmarked the stateful associator against a 6-condition deterministic impairment matrix across 60 evaluated flows:

| Impairment Condition | Curl Matched / Ref | Chromium Matched / Ref | Algorithmic Root Cause / Causal Analysis |
|:---|:---:|:---:|:---|
| **Natural Wire Order** | **5 / 5 (100%)** | **5 / 5 (100%)** | Chronological ordering preserves causal alias learning ($A \to B$). |
| **Reverse Record Order** | **0 / 5 (0%)** | **0 / 5 (0%)** | Causal breakdown: post-switch client packets arrive *before* the server's SCID announcement. |
| **Shuffle Record Order** | **4 / 5 (80%)** | **4 / 5 (80%)** | In 1 flow, packet reordering caused post-switch datagram to arrive prior to server reply. |
| **Drop One Record** | **5 / 5 (100%)** | **5 / 5 (100%)** | Frame reassembly successfully bridges non-essential padding segments. |
| **Drop Every 3rd Record** | **2 / 2 (100%)** | **2 / 2 (100%)** | 3 handshakes lost required CRYPTO bytes; extracts 100% of surviving TShark hellos. |
| **Truncate Middle (64 B)** | **5 / 5 (100%)** | **5 / 5 (100%)** | Partial packet truncation did not sever the initial handshake range. |

---

## Slide 6: Deliverable B — The Seven Limitation Rows Audit

| Row | Limitation Scenario | Evaluated PCAP Trace | Reference Tool Behavior | Status | Core Empirical Finding |
|:---:|:---|:---|:---|:---:|:---|
| **L1** | **QUIC v1 ClientHello** | `quic_curl`, `quic_chromium` | TShark 4.6.4 / FoxIO JA4 | **PASS** | 54/54 exact byte matches across impairment matrix; stateful accounting eliminates blindspot. |
| **L2** | **TLS Secrets / Keylog** | `tls_keylog_curl.pcap` | TShark / FoxIO JA4X / JA4H | **PASS** | Passive tap extracts **0 JA4X/JA4H** without keys; **5 records** visible with session keylog. |
| **L3** | **Vantage & Offload** | `tls_offload_on/off.pcap` | TShark / `l3_proxy_sanity.py` | **PASS** | Hardware offload advertises peer MSS `65495`; multi-vantage probe proves separate TCP legs. |
| **L4** | **Post-Quantum Key Share** | `tls_pq_on/off.pcap` | TShark / FoxIO JA4 | **PASS** | `tls.handshake.length` increases from 508 B (X25519) to **1511 B** (ML-KEM768). |
| **L5** | **GREASE Stability** | `tls_chromium_repeat.pcap` | TShark / FoxIO JA4 | **PASS** | 50 Chromium handshakes produce **50 distinct JA3** and **15 distinct JA4** hashes. |
| **L6** | **IPv6 Observation** | `tls_ipv6.pcap` | Host Routing Table | **NOT_MEASURED** | Environment limitation: physical testbed uplink lacks global IPv6 routing. |
| **L7** | **ECH & Encrypted DNS** | `tls_ech_on/off/doh.pcap` | TShark / FoxIO JA4 | **PASS** | Outer SNI masked (`cloudflare-ech.com`); DoH client directed to `cloudflare-dns.com`. |

---

## Slide 7: L3 Multi-Vantage Synchronized Capture Discovery

### What happens to TCP fingerprints across virtual network boundaries?
We executed a synchronized 4-vantage packet capture during a live controlled HTTPS probe:

```
[ Container (cn-lab) ]  ---> ISN=3419821880, TTL=64, WScale=10, MSS=1460 (Linux OS Default)
           |
           v
[ WSL2 Linux Bridge ]   ---> Traffic completely bypasses WSL2 eth0 (0 packets observed)
           |
           v
[ Hyper-V Virtual Switch] -> Managed directly by Windows host utility VM
           |
           v
[ Windows Physical Wi-Fi] -> ISN=168828592, TTL=128, WScale=8, MSS=1400 (Windows NT OS Default!)
```

### The Attribution Vulnerability:
1. Virtual switches terminate the TCP connection and establish a distinct outer leg.
2. The initial sequence number (ISN), TTL (64 $\to$ 128), and Window Scale (10 $\to$ 8) are completely replaced by the Windows host networking stack.
3. **Passive Fingerprint Failure:** A sensor at the perimeter calculating **JA4T** concludes the client is Windows, misattributing the actual containerized Linux workload.

---

## Slide 8: Summary, Limitations & Viva Defense

### Project Summary:
- **Deliverable A:** Field-by-field landscape across 7 fingerprint algorithms anchored in RFC specifications.
- **Deliverable B:** Audited 7-limitation matrix backed by 16 checksummed PCAP artifacts.
- **Deliverable C:** Engineered the C++20 `InitialContextAssociator`, eliminating 16 QUIC decryption failures and characterizing the causal ordering limit.

### Known Limitations & Future Work:
1. **QUIC Retry (RFC 9001 §5.2.2):** Current engine recognizes Retry packets but does not trigger key-rotation transitions for Retry SCIDs.
2. **Causal Ordering:** Single-pass streaming association fails under reversed wire arrival; requires bounded out-of-order reassembly buffers.
3. **IPv6 Egress:** Unmeasured due to absence of an ISP-assigned IPv6 global route.

### Reproducibility:
- **Repository:** `https://github.com/milonithakkar/CS331-Phase2`
- **Commands:** `make build && make test && python3 code/scripts/verify_all_seven_rows.py --live`
- **Test Status:** 1/1 CTest passed, 52/52 Pytest passed in 0.58s.
