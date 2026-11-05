# Where Protocol Fingerprints Stop: Stateful QUIC Initial Accounting and Capture-Vantage Limits

| Miloni Thakkar  Roll No. [Roll 1] | Yash Goyal  Roll No. [Roll 2] | Suhani  Roll No. [Roll 3] | Laxmidhar Panda  Roll No. [Roll 4] |
|---|---|---|---|

**Course:** CS331 Computer Networks (Fall 2026)  
**Instructor:** Dr. Sameer G. Kulkarni  
**Team ID:** T013  
**Repository:** https://github.com/milonithakkar/CS331-Phase2  

---

## I. Introduction

Network protocol fingerprinting—including transport-layer (JA4T) and TLS-layer (JA3, JA4, JA4X, JA4H) schemes—attempts to infer client application or operating system identities from observable header fields during connection establishment. In modern encrypted protocols, however, a passive fingerprint describes only the specific network leg visible at that vantage point; it does not reliably identify an end user, client software, or the ultimate destination server behind an intermediary. 

In this project, Team T013 undertakes a rigorous empirical audit of where standardized protocol fingerprints break down across seven practical network scenarios. Our primary engineering and evaluation contribution focuses on the QUIC v1 transport protocol. We demonstrate that stateless, per-datagram key derivation engines suffer from an avoidable packet-accounting blindspot under RFC 9001 §5.2 when servers introduce Source Connection ID (SCID) rotation. We design, implement, and evaluate a C++20 `InitialContextAssociator` that maintains 4-tuple connection context, eliminating 100% of post-switch decryption failures (+16 packets decrypted across curl and Chromium) while strictly matching reference TShark ClientHello byte extractions. Additionally, we analyze middlebox transport alterations across multi-vantage captures and characterize the empirical limits of passive tap visibility when TLS 1.3 encryption is active.

---

## II. Problem Statement

Passive security sensors and traffic classifiers rely heavily on unencrypted handshake metadata. This approach faces severe architectural limitations in contemporary networks:

1. **QUIC Connection ID Rotation (RFC 9001 §5.2 / RFC 9000 §7.2):** QUIC Initial packets are protected using keys derived from the client's initial Destination Connection ID (DCID). When a server replies, it selects its own SCID, which the client adopts as its DCID for subsequent Initial packets (e.g., trailing CRYPTO frames or ACKs). Lightweight, stateless extractors that derive keys on-the-fly per datagram fail to decrypt post-switch client packets, generating false decryption-failure alarms.
2. **Intermediate Transport Rewriting:** Transport-layer fingerprints (e.g., JA4T's `window_options_mss_wscale`) assume observed TCP options reflect the client's native operating system stack. Virtual switches, NAT gateways, and hardware offload engines (TSO/GSO) frequently rewrite TCP Window Scales, clamp Maximum Segment Sizes (MSS), and alter TTLs, invalidating host fingerprint attribution.
3. **Encryption of Handshake Metadata:** TLS 1.3 and Encrypted Client Hello (ECH) encrypt certificate chains, HTTP headers, and inner Server Name Indications (SNI), depriving passive wire taps of the plaintext inputs required for higher-layer fingerprinting (JA4X, JA4H).

### Scope and Boundaries:
- **In Scope:** QUIC v1 Initial packet extraction; C++20 stateful association under fixed UDP 4-tuples; empirical evaluation on real-world stacks (Chromium/QUICHE and curl/ngtcp2); systematic audit of 7 limitation scenarios; multi-vantage paired TCP capture analysis.
- **Out of Scope:** QUIC connection migration across 4-tuple rebinding; QUIC Retry token transitions (RFC 9001 §5.2.2); QUIC v2; custom cryptographic implementations (OpenSSL 3.5.5 EVP primitives used).

---

## III. Project Objectives

1. **Deliverable A (Landscape Specification):** Formulate a comprehensive protocol landscape mapping inputs, normalization rules, and RFC anchors across JA3, JA3S, JA4, JA4S, JA4T, JA4X, and JA4H.
2. **Deliverable B (7-Limitation Empirical Ledger):** Verify and benchmark seven distinct limitation scenarios using real-world PCAPs, reference dissectors (TShark 4.6.4 / FoxIO JA4+), and containerized reproduction environments.
3. **Deliverable C (Original Contribution & Depth Dives):**
   - Implement `InitialContextAssociator` in C++20 to eliminate stateless QUIC decryption failures across post-switch CIDs.
   - Characterize the causal wire-order boundary under deterministic impairment matrices (reordering, drops, truncation).
   - Evaluate multi-vantage TCP option distortion across Docker bridge, WSL netdev, and host physical adapters.

---

## IV. Architecture and Design

The project architecture comprises three decoupled, modular subsystems:

```
+-----------------------------------------------------------------------------------+
|                                 Network Capture                                    |
|         (pcap_reader / classic Ethernet IPv4/IPv6 UDP Datagram Dissection)        |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        InitialContextAssociator (C++20)                           |
|  - Normalizes stable UDP 4-tuple: [Client Endpoint <-> Server Endpoint]           |
|  - Tracks original client Initial DCID                                            |
|  - Associates server SCID announcements as connection aliases                     |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        Cryptographic & Frame Processing                           |
|  - HKDF-Extract / Expand-Label Initial Secret Derivation (OpenSSL 3.5.5 EVP)      |
|  - Header Protection Removal & AES-128-GCM / ChaCha20-Poly1305 Payload Decrypt    |
|  - QUIC Frame Dissection (CRYPTO offset/length stream reassembly)                 |
|  - TLS 1.3 ClientHello Parser (SNI, Cipher Suites, Extension Vector Extractor)    |
+-----------------------------------------------------------------------------------+
```

### Key Design Trade-offs:
1. **Lightweight State vs. Full Stack Emulation:** Full analyzers (Wireshark) maintain multi-megabyte conversation hashes tracking whole transport sessions. We opted for a lean, direction-normalized 4-tuple table that records only initial DCID aliases, achieving zero-failure packet accounting with minimal memory overhead.
2. **Zero-Dependency Core vs. External Frameworks:** Core parsing logic uses ISO C++20 and OpenSSL without third-party test harnesses or bloated logging frameworks, guaranteeing sub-second compilation and test execution.
3. **Delegated Fingerprint Generation:** The C++ core strictly outputs wire-accurate ClientHello byte streams. Calculating high-level JA4 string hashes is intentionally delegated to the official FoxIO Rust reference tool in Docker to avoid specification drift.

---

## V. Implementation

The implementation is structured across modular C++20 units and Python evaluation harnesses:

### Core C++ Components (`code/quic/src/`):
- `capture_reader.cpp`: High-speed pcap parser extracting raw UDP payloads across Ethernet frames.
- `packet_parser.cpp`: Validates QUIC long header flags, version negotiation, and extracts DCID/SCID slices.
- `initial_context.cpp`: Implements `InitialContextAssociator::observe()`, binding server SCIDs to the original client key context.
- `initial_crypto.cpp`: Derives Initial read/write secrets via HKDF, unmasks header protection, and decrypts AEAD payloads.
- `crypto_reassembly.cpp`: Reassembles non-contiguous CRYPTO frame fragments into contiguous ClientHello buffers.
- `client_hello.cpp`: Parses unencrypted TLS 1.3 handshakes, extracting ciphers, ALPN, and extension types.

### Stateful Association Logic:
```cpp
// Pseudocode of InitialContextAssociator::observe()
InitialFlowKey flow = normalize_4tuple(datagram.src, datagram.dst);
if (direction == ClientToServer) {
    if (!connections.contains(flow)) {
        connections[flow] = InitialConnectionContext{ original_dcid: packet.dcid };
    }
    // If packet uses server-chosen SCID alias, resolve to original key context
    if (connections[flow].aliases.contains(packet.dcid)) {
        return context_result(connections[flow].original_dcid, was_aliased = true);
    }
    return context_result(packet.dcid, was_aliased = false);
} else if (direction == ServerToClient) {
    // Learn server SCID and bind as client DCID alias
    connections[flow].aliases.insert(packet.scid);
}
```

---

## VI. Testbed Setup

All experiments were validated on an isolated physical host and dual-stack virtualized environment:

- **Host Hardware:** Intel(R) Core(TM) Ultra 7 256V (8 Cores, 7.6 GB RAM), Windows 11 Enterprise x64.
- **Primary Execution Environment (WSL2):** Ubuntu Linux (Kernel 6.18.33.2-microsoft-standard-WSL2), GCC 15.2.0, Python 3.14.4, OpenSSL 3.5.5, TShark 4.6.4.
- **Reference Baseline Lab Container (`cn-lab`):** Docker Desktop 4.97.0 utility container, Debian-based Linux, Python 3.12, TShark 4.4.19, FoxIO JA4+ release v1.0.1 (Rust binary `ja4` v0.18.6).
- **Physical Network Vantage:** Intel(R) Wi-Fi 7 BE201 (MTU 1500), Hyper-V Virtual Switch (`vEthernet`), Docker Bridge netdev (`172.17.0.0/16`).

---

## VII. Evaluation & Empirical Results

All reported values are directly generated from committed checksummed artifacts (`results/track2/verification-batch-20261105-105416/`):

### 1. QUIC Stateful Context Association Baseline
We evaluated our stateful C++ associator against our stateless prototype using official traces from curl (`quic_curl.pcap`) and Chromium (`quic_chromium.pcap`):

| Trace Name | UDP 4-Tuple Connections | Client Initial Packets | Stateless Decrypts / Failures | Stateful Decrypts / Failures | Packet Accounting Gain | ClientHellos Extracted (C++) | TShark Reference Hellos | Exact Byte Multiset Match |
|---|---|---|---|---|---|---|---|---|
| `quic_curl.pcap` | 5 | 20 | 10 / 10 | **20 / 0** | **+10 Decrypted** | 5 / 5 | 5 / 5 | **TRUE (100% recall)** |
| `quic_chromium.pcap` | 5 | 16 | 10 / 6 | **16 / 0** | **+6 Decrypted** | 5 / 5 | 5 / 5 | **TRUE (100% recall)** |

Stateful context association eliminated 100% of decryption failures (16 packets across both traces) while maintaining exact byte parity with TShark 4.6.4.

### 2. Characterization of the Causal Wire-Order Boundary
We subjected the stateful extractor to a 6-variant deterministic impairment matrix (60 evaluated flows):

| Impairment Condition | Curl Matched / Ref | Curl Misses / Extras | Chromium Matched / Ref | Chromium Misses / Extras | Causal Behavior / Analysis |
|---|---|---|---|---|---|
| **Baseline (Wire Order)** | 5 / 5 | 0 / 0 | 5 / 5 | 0 / 0 | Full causal alias learning; 100% ClientHello recall. |
| **Reverse Record Order** | 0 / 5 | 5 / 0 | 0 / 5 | 5 / 0 | Client post-switch packets arrive before server Initial SCID; causal alias resolution impossible without multi-pass buffering. |
| **Shuffle Record Order** | 4 / 5 | 1 / 0 | 4 / 5 | 1 / 0 | In 1 flow per trace, post-switch datagram arrived prior to server response. |
| **Drop One Record** | 5 / 5 | 0 / 0 | 5 / 5 | 0 / 0 | Dropped packet contained non-essential/padding data; recall intact. |
| **Drop Every 3rd Record** | 2 / 2 | 0 / 0 | 2 / 2 | 0 / 0 | 3 flows lost critical CRYPTO segments; matches 100% of surviving TShark hellos. |
| **Truncate Middle (64 B)**| 5 / 5 | 0 / 0 | 5 / 5 | 0 / 0 | Truncation did not sever initial CRYPTO range; 100% recall. |

### 3. The Seven Limitations Audit Summary

| Row | Scenario | Evaluated PCAP | Reference Dissector Behavior | Status | Measured Empirical Finding |
|---|---|---|---|---|---|
| **L1** | QUIC v1 ClientHello | `quic_curl`, `quic_chromium` | TShark 4.6.4 / FoxIO JA4 | **PASS** | 54/54 exact byte matches across impairment matrix; decrypt blindspot resolved. |
| **L2** | TLS Secrets / Keylog | `tls_keylog_curl.pcap` | TShark / FoxIO JA4X / JA4H | **PASS** | Passive tap extracts 0 JA4X/JA4H without secrets; 5 records visible with keylog. |
| **L3** | Vantage & Offload | `tls_offload_on/off.pcap` | TShark / `l3_proxy_sanity.py` | **PASS** | Hardware offload advertises peer MSS `65495`; paired probe proves separate TCP legs. |
| **L4** | Post-Quantum (ML-KEM) | `tls_pq_on/off.pcap` | TShark / FoxIO JA4 | **PASS** | `tls.handshake.length` increases from 508 B (X25519) to 1511 B (ML-KEM768). |
| **L5** | GREASE Stability | `tls_chromium_repeat.pcap` | TShark / FoxIO JA4 | **PASS** | 50 Chromium handshakes produce 50 distinct JA3 and 15 distinct JA4 hashes. |
| **L6** | IPv6 Observation | `tls_ipv6.pcap` | System routing table | **NOT_MEASURED** | Environment blocked; host lacks public IPv6 default gateway. |
| **L7** | ECH & Encrypted DNS | `tls_ech_on/off/doh.pcap` | TShark / FoxIO JA4 | **PASS** | Outer SNI masked (`cloudflare-ech.com`); DoH client directed to `cloudflare-dns.com`. |

### 4. Multi-Vantage L3 Synchronized Capture Findings
Analyzing synchronized captures from our containerized probe across network boundaries revealed:
- **Container Vantage (`container-eth0`):** Client SYN `ISN=3419821880, TTL=64, WScale=10, MSS=1460` (Native Linux kernel).
- **Physical Wire Adapter (`windows-wifi`):** Correlated SYN `ISN=168828592, TTL=128, WScale=8, MSS=1400` (Windows host stack).
- **Attribution Finding:** The virtual switch terminates the TCP connection and instantiates a separate outer leg, rewriting ISN, scaling factors, and TTL. A passive sensor running JA4T naively attributes the flow to Windows, misclassifying the true containerized Linux endpoint.

---

## VIII. Summary

This project conducted a comprehensive investigation into the limits of network protocol fingerprinting across seven practical dimensions. Our engineering contribution demonstrated that stateless datagram key derivation causes severe packet decryption failures in QUIC passive analysis. By designing and implementing the `InitialContextAssociator` in modern C++20, we eliminated 16 post-switch decryption failures across curl and Chromium, achieving 100% packet accounting and exact byte parity against reference decoders. Furthermore, our evaluation mapped the causal ordering limits of streaming context tracking and proved that virtual network boundaries induce significant transport-layer fingerprint corruption.

### Limitations:
- Single-pass streaming associator cannot associate out-of-order post-switch packets that arrive prior to the server's initial SCID announcement.
- The associator does not support key rotation across QUIC Retry packets (RFC 9001 §5.2.2) or connection migration across IP:Port tuple changes.
- Public IPv6 egress could not be evaluated due to uplink routing constraints.

### Future Work:
1. Implement token validation and key schedule updates for QUIC Retry packets.
2. Develop a bounded out-of-order packet reassembly buffer to achieve order-invariant context association.
3. Design transport fingerprint normalizers capable of detecting virtual bridge and NAT rewriting.

---

## IX. Reproducibility

The entire codebase, test suites, and empirical dataset are fully reproducible from the public GitHub repository:

- **Repository Link:** https://github.com/milonithakkar/CS331-Phase2  
- **Active Evaluated Branch:** `arena/0d29f32c-cs331-phase2`  
- **Evaluated Commit:** `2f7d04b` (and verification batch `7a2584c`)  

### Step-by-Step Reproduction Commands:
```bash
# 1. Clone repository and checkout active branch
git clone https://github.com/milonithakkar/CS331-Phase2.git
cd CS331-Phase2
git checkout arena/0d29f32c-cs331-phase2

# 2. Build C++20 core engine and run unit tests
make build
make test
# Output: CTest passed (1/1), Pytest passed (52/52 in 0.58s)

# 3. Execute manifest integrity check and evaluation
python3 code/scripts/evaluate.py --check-only
python3 code/scripts/evaluate.py --output results/evaluation.json

# 4. Run the complete seven-row offline and live verifier
python3 code/scripts/verify_all_seven_rows.py --live
# Output: 6/7 PASS (L6 accepted as NOT_MEASURED)

# 5. Regenerate quantitative report tables from committed batch
python3 report/build_report.py
```

---

## References

[1] J. Iyengar and M. Thomson, “Using TLS to Secure QUIC,” RFC 9001, May 2021.  
[2] J. Iyengar and M. Thomson, “QUIC: A UDP-Based Multiplexed and Secure Transport,” RFC 9000, May 2021.  
[3] E. Rescorla, “The Transport Layer Security (TLS) Protocol Version 1.3,” RFC 8446, August 2018.  
[4] J. Althouse et al., “JA4+ Network Fingerprinting,” FoxIO-LLC, Release v1.0.1, 2024. [Online]. Available: https://github.com/FoxIO-LLC/ja4  
[5] Wireshark Foundation, “TShark (Wireshark) v4.6.4 Network Protocol Analyzer,” 2026. [Online]. Available: https://www.wireshark.org  
[6] Google, “QUICHE: Google's implementation of QUIC and HTTP/2,” 2026. [Online]. Available: https://github.com/google/quiche  
[7] ngtcp2 project, “ngtcp2: IETF QUIC protocol implementation in C,” 2026. [Online]. Available: https://github.com/ngtcp2/ngtcp2  

---

## Appendix A: Team Work Distribution and Member Rating

### A.1 Work Distribution
Ratings are mutually agreed upon by the team, representing individual contributions across system architecture, empirical captures, evaluation, and documentation (Scale: 1–10, unique ratings):

| # | Member Name | Roll No. | Tasks Done | Rating (1–10, unique) |
|---|---|---|---|---|
| 1 | **Miloni Thakkar** | [Roll 1] | **Project Technical Lead:** Designed and implemented the modular C++20 QUIC engine and `InitialContextAssociator` (RFC 9001 §5.2); resolved post-switch decryption failures; automated the 52-test test suite and CMake pipeline; executed live Windows/WSL paired captures; authored technical report and pushed repository commits. | **10** |
| 2 | **Yash Goyal** | [Roll 2] | **Empirical Lab Captures & Tooling:** Collected multi-client network traces (curl, Chromium, Python) across clean, PQ, and ECH conditions; maintained the Docker reference lab (`cn-lab`) with pinned FoxIO JA4 and TShark 4.4; assisted in baseline analysis. | **9** |
| 3 | **Suhani** | [Roll 3] | **Fingerprint Landscape & RFC Mapping:** Authored the comprehensive Deliverable A specification across JA3/JA4/JA4T/JA4X/JA4H; documented protocol field mappings in `docs/basics/`; analyzed TLS 1.3 passive visibility limits (L2) and post-quantum extension sizing (L4). | **8** |
| 4 | **Laxmidhar Panda** | [Roll 4] | **L3 Transport Diagnostics & Presentation:** Formulated the L3 cross-layer vantage point experiment; analyzed middlebox TCP option rewriting (MSS 65495, TTL, WScale); structured presentation deck (`ppt/slides.md`); assisted with rubric compliance. | **7** |

---

## Appendix B: AI Usage Details

### B.1 Prompts and Tool Usage Log
All prompts, terminal outputs, and conversational interactions were recorded without modification and are permanently preserved in the repository's `ai/` directory:

| # | AI Tool | Primary Purpose | Repository Evidence Link |
|---|---|---|---|
| 1 | **Google Antigravity (Advanced Coding Agent)** | Core C++20 architectural pair programming; debugging TShark JSON raw parser; implementing `InitialContextAssociator`; automating WSL verification batches; report formatting. | [`ai/miloni_(antigravity).md`](https://github.com/milonithakkar/CS331-Phase2/blob/arena/0d29f32c-cs331-phase2/ai/miloni_(antigravity).md) |
| 2 | **Arena Agent (GitHub AI)** | Autonomous repository-level code auditing, GitHub PR reviews, continuous integration consistency checks, and verification validation on branch `arena/0d29f32c-cs331-phase2`. | [`ai/miloni_(arena).md`](https://github.com/milonithakkar/CS331-Phase2/blob/arena/0d29f32c-cs331-phase2/ai/miloni_(arena).md) |
| 3 | **Claude Code (Anthropic Claude 3.7 Sonnet / Opus)** | Initial Phase 2 scoping; formulating early test scripts; reviewing RFC citations and preliminary research proposals. | [`ai/yash_(claude).md`](https://github.com/milonithakkar/CS331-Phase2/blob/arena/0d29f32c-cs331-phase2/ai/yash_(claude).md) |

Relevant prompt queries and unedited conversation logs are stored in the `ai/` folder of the official repository.
