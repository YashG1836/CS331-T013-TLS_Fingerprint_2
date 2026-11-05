# Where Protocol Fingerprints Stop
## Stateful QUIC Initial Accounting and Capture-Vantage Limits in Modern Encrypted Transports

**CS331 Computer Networks (Fall 2026) — Final Project Submission**  
**Instructor:** Dr. Sameer G. Kulkarni | **Team ID:** T013  
**Team Members:**
- **Miloni Thakkar** (`24110204`) — *Project Lead & Systems Architecture*
- **Suhani** (`24110358`) — *Architecture Co-Design & Quality Verification*
- **Yash Goyal** (`24110399`) — *Empirical Lab Captures & Tooling*
- **Laxmidhar Panda** (`24110185`) — *Transport Diagnostics & Presentation*

---

## 📌 Executive Summary

Modern network fingerprinting algorithms (such as JA3, JA4, and JA4T) operate under the assumption that observable handshake metadata accurately identifies client applications and operating systems. In real-world networks, however, **a passive wire tap only observes the immediate network leg**, not the true endpoint.

This project delivers a two-fold contribution:
1. **Systems Contribution (C++20 & OpenSSL 3):** We identified and resolved an architectural decryption blindspot in stateless QUIC parsers under RFC 9001 §5.2. When servers rotate Destination Connection IDs (DCIDs), stateless decoders fail to decrypt subsequent client Initial datagrams. We engineered an `InitialContextAssociator` in C++20 that maintains UDP 4-tuple flow state, achieving **100% packet decryption accounting (+16 packets decrypted, 0 failures)** and **100% byte-for-byte ClientHello parity with TShark 4.6.4**.
2. **Empirical Measurement Contribution:** We benchmarked 7 practical protocol limitations (L1–L7) across 16 checksummed PCAP artifacts, evaluated 60 impairment flows to map the causal wire-ordering limits of QUIC, and revealed through multi-vantage captures how virtual switches rewrite TCP parameters (ISN, TTL 64 $\to$ 128, WScale 10 $\to$ 8) to disguise a Linux container as a native Windows host.

---

## 🚀 Quick Start (One-Line Reproduction)

Clone the repository and run the automated verification suite:

```bash
# 1. Build the C++20 QUIC engine and run all unit & integration tests
make test
# Output: CTest 1/1 passed (0.01s), Pytest 52/52 passed (0.44s)

# 2. Validate all 16 committed PCAP artifacts against manifest checksums
make check
# Output: manifest valid: 16 capture(s) (15 with packets, 1 empty, 16 provisional)

# 3. Run the live 7-limitation audit across all experimental rows
python3 code/scripts/verify_all_seven_rows.py --live
# Output: 6/7 PASS (L1, L2, L3, L4, L5, L7 PASS; L6 accepted as NOT_MEASURED)

# 4. Regenerate quantitative report tables from verification batches
python3 report/build_report.py
```

---

## 📊 Key Results & Empirical Findings

### 1. QUIC Stateful Decryption Breakthrough (RFC 9001 §5.2)

Stateless analyzers derive Initial keys from the DCID of each packet independently. When a server responds and assigns a new Source CID (SCID), subsequent client Initial datagrams adopt this new CID as their destination, causing stateless decoders to fail. Our stateful associator maps the server alias back to the original client DCID context.

| Metric | `quic_curl.pcap` (Baseline) | `quic_curl.pcap` (Stateful Engine) | `quic_chromium.pcap` (Baseline) | `quic_chromium.pcap` (Stateful Engine) |
|:---|:---:|:---:|:---:|:---:|
| **UDP 4-Tuple Connections** | 5 | 5 | 5 | 5 |
| **Total Client Initial Packets** | 20 | 20 | 16 | 16 |
| **Decrypted Client Packets** | 10 (50.0%) | **20 (100.0%)** | 10 (62.5%) | **16 (100.0%)** |
| **Decryption Failures** | 10 (50.0%) | **0 (0.0%)** | 6 (37.5%) | **0 (0.0%)** |
| **Net Accounting Gain** | Baseline | **+10 Packets** | Baseline | **+6 Packets** |
| **Complete ClientHellos** | 5 / 5 | 5 / 5 | 5 / 5 | 5 / 5 |
| **TShark 4.6.4 Reference Byte Parity** | 5 / 5 (100%) | **5 / 5 (100%)** | 5 / 5 (100%) | **5 / 5 (100%)** |

> **Result:** 100% of client Initial packets decrypted across both live network traces with zero decryption errors and zero false misses against reference dissectors.

---

### 2. The 7 Protocol Limitation Rows Audit

| Row | Limitation Scenario | PCAP Artifact | Status | Key Empirical Finding |
|:---:|:---|:---|:---:|:---|
| **L1** | **QUIC v1 ClientHello** | `quic_curl`, `quic_chromium` | **PASS** | 54/54 exact byte matches across impairment matrix; stateful associator eliminates post-switch CID blindspot. |
| **L2** | **TLS Secrets & Keylog** | `tls_keylog_curl.pcap` | **PASS** | Passive tap extracts **0 JA4X/JA4H** without secrets; injecting `SSLKEYLOGFILE` unlocks all 5 HTTP/2 & cert records. |
| **L3** | **Vantage & HW Offload** | `tls_offload_on/off.pcap` | **PASS** | Hardware offload engine alters peer MSS to 65495; multi-vantage probe proves container TCP leg is rewritten to Windows NT. |
| **L4** | **Post-Quantum Key Share** | `tls_pq_on/off.pcap` | **PASS** | ML-KEM768 expands `tls.handshake.length` from 508 B to **1511 B**, forcing TCP segmentation across MTU boundary. |
| **L5** | **GREASE Hash Stability** | `tls_chromium_repeat.pcap` | **PASS** | 50 repeated handshakes produce **50 distinct JA3 hashes** (0% stability) and **15 distinct JA4 hashes** due to randomized extension ciphers. |
| **L6** | **IPv6 Observation** | `tls_ipv6.pcap` | **NOT_MEASURED** | Environment limitation: physical lab uplink lacks global IPv6 routing (`connect: Network is unreachable`). |
| **L7** | **ECH & Encrypted DNS** | `tls_ech_on/off/doh.pcap` | **PASS** | Outer SNI masked to `cloudflare-ech.com`; DoH DNS queries routed to `cloudflare-dns.com`, blinding wire monitors. |

---

### 3. Causal Wire-Ordering Limits (60 Impaired Flows)

We subjected our C++20 engine to a 6-condition deterministic impairment matrix across 60 flows to establish the formal boundary of single-pass stream processing:

* **Natural Wire Order:** **100% (5/5)** match for curl and Chromium.
* **Reverse Record Order:** **0% (0/5)** match — when post-switch client datagrams arrive before the server's SCID announcement, single-pass streaming association breaks down causally.
* **Shuffle Record Order:** **80% (4/5)** match — flows preserve association as long as local causality between server Initial and subsequent client datagrams holds.
* **Packet Loss & Truncation:** Frame reassembly gracefully bridges missing padding and extracts 100% of surviving handshakes.

---

## 📁 Repository Directory Structure

```
CS331-Phase2/
├── CMakeLists.txt              # C++20 CMake build configuration
├── Makefile                    # Standard targets: build, test, check, eval
├── pyproject.toml              # Python environment and test tooling
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation and reproduction guide
│
├── report/                     # Formal project report deliverables
│   ├── CS331_Phase2_Report_T013.docx  # Mandated 2-column Word document (Times New Roman 10 pt)
│   ├── report_formal.md        # Formatted markdown source of the formal report
│   └── build_report.py         # Automated report generation script
│
├── ppt/                        # Presentation slides deliverables
│   ├── CS331_Phase2_Presentation_T013.pptx # Official 16:9 widescreen presentation deck
│   └── slides_formal.md        # Slide deck outline and speaking notes
│
├── code/                       # Source code
│   ├── quic/                   # Modular C++20 QUIC v1 engine
│   │   ├── src/                # Packet parser, crypto, frame reassembly, stateful context
│   │   └── tests/              # GoogleTest / CTest verification suite
│   └── scripts/                # Python evaluation, verification, and baseline runners
│
├── captures/                   # Empirical network traces
│   ├── pcaps/                  # 16 committed PCAP artifacts (QUIC, ECH, PQ, Offload, Keylog)
│   ├── metadata/               # Per-capture environment and command metadata JSONs
│   └── manifest.json           # Cryptographic checksum manifest (source of truth)
│
├── results/                    # Ground-truth experimental results
│   ├── track2/                 # Verification batch (batch 20261105-105416)
│   └── evaluation.json         # Automated evaluation report output
│
├── docs/                       # Specifications and background documentation
│   ├── landscape.md            # Deliverable A: JA3 vs JA4+ comparison table
│   ├── glossary.md             # RFC protocol terminology and definitions
│   └── reading-guide.md        # Technical RFC reading guide
│
└── ai/                         # Transparent AI usage records
    ├── README.md               # Attestation and disclosure guide
    ├── miloni_(antigravity).md # Google Antigravity pair-programming transcript
    ├── miloni_(arena).md       # Complete 164-turn Arena web agent transcript
    └── yash_(claude).md        # Claude Code prompt logs
```

---

## 📄 Key Project Deliverables

- **Formal Report:** [`report/CS331_Phase2_Report_T013.docx`](report/CS331_Phase2_Report_T013.docx) (Mandated 2-column Word template, Sections I–IX + Appendices A & B).
- **Presentation Deck:** [`ppt/CS331_Phase2_Presentation_T013.pptx`](ppt/CS331_Phase2_Presentation_T013.pptx) (Widescreen 16:9 PowerPoint deck).
- **Technology Decision Record:** [`DECISIONS.md`](DECISIONS.md) (Architecture rationale: C++20 for systems core vs Python for research orchestration).
- **Audit Ledger:** [`LEDGER.md`](LEDGER.md) (Detailed per-row evidence commands and reproduction status).
- **Full Architecture Plan:** [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) (15-day technical plan and component breakdown).
- **Original Proposal:** [`PROJECT2_PROPOSAL.md`](PROJECT2_PROPOSAL.md) (Initial approved project proposal).

---

## 🛠️ CLI Usage Guide

The custom C++20 QUIC engine supports both raw hex datagram inspection and offline PCAP analysis:

```bash
# 1. Inspect a raw hex datagram:
./build/code/quic/src/quic-fingerprint --hex '<hex-bytes>'

# 2. Analyze a QUIC PCAP in stateless mode:
./build/code/quic/src/quic-fingerprint --pcap captures/pcaps/quic_curl.pcap

# 3. Analyze a QUIC PCAP in stateful association mode (RFC 9001 §5.2):
./build/code/quic/src/quic-fingerprint --pcap captures/pcaps/quic_curl.pcap --stateful-initial-context
```

### Makefile Targets

* `make build`: Configures CMake in Release mode and compiles all C++ targets.
* `make test`: Runs both `ctest` (C++ unit tests) and `pytest` (52 integration tests).
* `make check`: Verifies that all 16 PCAP files match their declared SHA-256 hashes in `manifest.json`.
* `make eval`: Runs the evaluation pipeline and generates `results/evaluation.json`.
* `make clean`: Removes build caches and temporary artifacts.

---

## 📜 Academic Integrity & AI Transparency

In accordance with course guidelines, all AI interactions have been preserved in unedited form within the [`ai/`](ai/) directory:
- [`ai/miloni_(antigravity).md`](ai/miloni_(antigravity).md): Google Antigravity pair-programming session.
- [`ai/miloni_(arena).md`](ai/miloni_(arena).md): Complete 164-turn web agent transcript.
- [`ai/yash_(claude).md`](ai/yash_(claude).md): Claude Code prompt log.

---
*CS331 Computer Networks (Fall 2026) — Department of Computer Science & Engineering*
