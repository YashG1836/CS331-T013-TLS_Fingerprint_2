# Where Protocol Fingerprints Stop
### Seven limits of real TLS fingerprinting tools, and a stateful QUIC Initial extractor

**CS331 Computer Networks, Project 2** | **Instructor:** Dr. Sameer G. Kulkarni | **Team T013**

| Member | Roll No. | Main work |
|---|---|---|
| Miloni Thakkar | 24110204 | C++ QUIC extractor, stateful associator, WSL batches, L3 paired capture, report |
| Suhani | 24110358 | Architecture co-design, verification, fingerprint landscape (Deliverable A) |
| Yash Goyal | 24110399 | Docker lab, Track 1 captures and analysis (L1 to L7) |
| Laxmidhar Panda | 24110185 | L3 transport analysis, presentation |

---

## The idea in 5 lines
1. Web traffic is encrypted, but the first message of every connection (the **ClientHello**) is not.
2. Each TLS library fills it a bit differently, so a hash of it works like a **fingerprint** (JA3, JA4). Networks use it to recognise apps without decrypting.
3. In Phase 1 we wrote our own fingerprint code. Our professor said: don't rebuild it; take the tools people really use (**Wireshark/TShark** in C, **FoxIO ja4** in Rust) and find **where they stop working**.
4. **Track 1:** real captures in 7 situations (QUIC, no keys, capture point, post-quantum, repeats, IPv6, ECH). Each is one test with one number.
5. **Track 2:** our own C++ QUIC Initial extractor, checked byte for byte against TShark, which handles the connection ID switch of RFC 9001 §5.2.

---

## Main results

### Track 1: seven limitations (details in [`LEDGER.md`](LEDGER.md) and [`docs/tests/`](docs/tests/README.md))

| Row | Question | What we measured | Status |
|---|---|---|---|
| L1 | Can tools read QUIC? | TShark and FoxIO: 5/5 ClientHellos for curl and Chromium, even when split into 21 CRYPTO pieces | Our guess was wrong: they can |
| L2 | Which fingerprints need TLS keys? | JA4X + JA4H: 0 without keys, 5 with keys | Confirmed |
| L3 | Does the capture point matter? | Offload on: hello in 1 frame of 1586 B; off: 1514 + 138 B. SYN-ACK MSS 65495 came from Docker's proxy, not the server. On Windows, the container's connection leaves the Wi-Fi as a Windows TCP connection (TTL 128, wscale 8) | Confirmed |
| L4 | Post-quantum key share | ClientHello 508 B (X25519) vs 1511 B (X25519MLKEM768); JA4 changes (14 vs 12 extensions) | Confirmed |
| L5 | One browser = one fingerprint? | Chromium, 50 hellos: 50 JA3s. JA4: **15** with TShark 4.6.8 and FoxIO v0.18.6, **1** with FoxIO v1.0.1 (GREASE in signature algorithms) | Confirmed: JA4 depends on tool version |
| L6 | IPv4 vs IPv6 | IPv6 capture has 0 packets: no IPv6 route on our networks | Not measured |
| L7 | Does ECH hide the site? | ECH on: SNI shows `cloudflare-ech.com`, but plain DNS still asks for `crypto.cloudflare.com`. The DoH run did not load on campus | Confirmed; DoH not measured |

### Track 2: our C++ QUIC Initial extractor

After the server answers, the client sends its next Initial packets to the server's new connection ID (RFC 9000 §7.2), but their keys still come from the **first** connection ID (RFC 9001 §5.2). An extractor that makes keys from each packet's own ID fails on those packets. Our `--stateful-initial-context` mode remembers the first ID per UDP 4-tuple.

| | curl | Chromium |
|---|---|---|
| client Initial packets | 20 | 16 |
| decrypted, stateless (keys from each packet's DCID) | 10 | 10 |
| decrypted, stateful (keys from the first DCID) | **20** | **16** |
| complete ClientHellos (both modes) | 5/5, same bytes as TShark 4.6.4 | 5/5, same bytes as TShark 4.6.4 |

- TShark already decrypts these packets; stateful mode makes our extractor match it. In our pcaps the later packets carry only ACK + PADDING, so the ClientHello and JA4 do not change.
- Damaged copies, stateless mode: 54/54 ClientHellos equal to TShark (6 damage cases × 2 pcaps).
- Damaged copies, stateful mode: **reverse order 0/5, shuffle 4/5** per pcap. If a later packet arrives first, the stateful mode picks the wrong ID as the key source. This is a known limit (see [`docs/quic/implementation-status.md`](docs/quic/implementation-status.md)).

---

## How to run it

```bash
make test     # build the C++ code, run CTest (1/1) and pytest (52 tests)
make check    # every committed pcap matches its SHA-256 in captures/manifest.json (16 captures)
python3 code/scripts/verify_all_seven_rows.py   # offline audit of L1-L7: 6/7 PASS, L6 NOT_MEASURED
make lab-image && make lab-eval                 # Docker lab: rerun TShark + FoxIO on all pcaps
```

C++ extractor:
```bash
./build/code/quic/src/quic-fingerprint --pcap captures/pcaps/quic_curl.pcap                              # stateless
./build/code/quic/src/quic-fingerprint --pcap captures/pcaps/quic_curl.pcap --stateful-initial-context   # stateful
```
Needs CMake, a C++20 compiler and OpenSSL 3 headers (`libssl-dev`). The C++ tests are a plain test program run by CTest; no external test framework.

---

## Folder structure

```
report/      formal report (CS331_Phase2_Report_T013.docx) and its markdown source
ppt/         presentation (CS331_Phase2_Presentation_T013.pptx) and its slide text (slides_formal.md)
code/quic/   C++20 QUIC Initial extractor: pcap reader, packet parser, keys, decrypt, CRYPTO reassembly, ClientHello
code/scripts Python: Track 1 capture/analyze, impairment tests, verifiers
captures/    16 pcaps, manifest.json with hashes, per-capture metadata
results/     Track 1 summary, re-check, Track 2 batches, L3 paired run
docs/        tests T0-T7, fingerprint landscape, glossary, reading guide
ai/          our AI prompts and transcripts, unedited
```

Other documents: [`DECISIONS.md`](DECISIONS.md) (why C++ and Python), [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md), [`PROJECT2_PROPOSAL.md`](PROJECT2_PROPOSAL.md), [`docs/landscape.md`](docs/landscape.md) (JA3 vs JA4+ fields), [`docs/glossary.md`](docs/glossary.md).

## What we did not cover
- Track 1 was captured inside Docker on a Mac, behind Docker's proxy; one network (campus) with no IPv6 and DoH blocked.
- One site (Cloudflare), three clients (Chromium, curl, Python). TLS 1.2 not tested.
- QUIC Retry, connection migration, QUIC v2. The stateful mode is sensitive to packet order.

## AI use
All prompts and transcripts are kept unedited in [`ai/`](ai/): `miloni_(antigravity).md`, `miloni_(arena).md`, `yash_(claude).md`.
