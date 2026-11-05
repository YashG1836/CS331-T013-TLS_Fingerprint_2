# Slides: text and speaker notes

Text of `CS331_Phase2_Presentation_T013.pptx` (8 slides), with what to say on each slide.
Every number here is also in `LEDGER.md`, `docs/tests/` or `results/`.

---

## 1. Where do real TLS fingerprinting tools stop working?
Seven limits of TShark and FoxIO ja4 on real captures, and our own QUIC Initial extractor in C++.

| Member | Roll No. | Main work |
|---|---|---|
| Miloni Thakkar | 24110204 | C++ QUIC extractor, WSL batches, L3 paired capture |
| Suhani | 24110358 | Design, verification, fingerprint landscape |
| Yash Goyal | 24110399 | Docker lab, Track 1 captures (L1 to L7) |
| Laxmidhar Panda | 24110185 | L3 TCP analysis, presentation |

**Say:** In Phase 1 we wrote our own fingerprint code. Sir asked us to take the tools people really use, TShark and FoxIO ja4, find where they stop working, and look at QUIC. Track 1 is seven real-capture tests. Track 2 is our own C++ QUIC Initial extractor.

---

## 2. What a fingerprint is, and what we did
- JA4 of Chromium from our capture: `t13d1517h2_8daaf6152771_cb7bf5808d99`
  - `t13d1517h2`: TCP, TLS 1.3, has a site name, 15 ciphers, 17 extensions, HTTP/2
  - `8daaf6152771`: hash of the cipher list, sorted
  - `cb7bf5808d99`: hash of the extensions and signature algorithms, sorted
- Phase 1: our own JA3/JA4 code in Python; some numbers did not come back when re-run.
- Phase 2: use the real tools, find where they break, do QUIC.
- Every test: change one thing, capture with tcpdump (Linux in Docker), read with TShark (C) and FoxIO ja4 (Rust), save one number with its pcap.

**Say:** The ClientHello is the first message and is not encrypted. A fingerprint points to a TLS library and its settings, never to a person. We do not compute fingerprints ourselves.

---

## 3. Seven limitations at a glance

| | What changed | Question | What we saw | Status |
|---|---|---|---|---|
| L1 | QUIC | Can the tools read the ClientHello? | Yes: 5/5, even when split into 21 pieces | Guess was wrong |
| L2 | TLS 1.3 encrypts the certificate | Which fingerprints need the keys? | JA4X + JA4H: 0 without keys, 5 with keys | Confirmed |
| L3 | Offload, proxies | Does the capture point matter? | 1 frame of 1586 B vs 1514 + 138 B; MSS 65495 from Docker | Confirmed |
| L4 | Post-quantum key share | Does a bigger hello change JA4? | 508 B to 1511 B; JA4 changes | Confirmed |
| L5 | GREASE, shuffling | Is one browser one JA4? | 15 JA4s or 1, depending on the tool version | Confirmed |
| L6 | IPv6 | Does the IP version matter? | No IPv6 route: capture has 0 packets | Not measured |
| L7 | ECH | Is the site name hidden? | Hidden in TLS, still visible in DNS | Confirmed |

**Say:** One row per test; each has its own file in `docs/tests/` with what it does not prove.

---

## 4. L5: one Chromium gives 15 JA4s or 1, depending on the tool
Same pcap, same 50 ClientHellos from Chromium 156.
- **50** different JA3s: JA3 keeps the extension order, and Chromium shuffles it.
- **15** different JA4s: TShark 4.4.19 and 4.6.8, FoxIO ja4 v0.18.6.
- **1** JA4: FoxIO ja4 v1.0.1 (Aug 2026) and FoxIO main.
- Why: Chromium puts a random GREASE value (RFC 8701) first in its signature algorithms; 15 different values appear. FoxIO fixed this in commit d66336e, first released in v1.0.1. TShark 4.6.8 still counts it.
- Meaning: a JA4 list made with one tool misses most Chromium connections seen by another. Store the tool and version with every fingerprint. Control: curl and Python gave 1 JA3 and 1 JA4 each.

**Say:** It is not a new bug; FoxIO already fixed it. What we show is that tools in use today still disagree. Commands: `results/track1/recheck-20261106.md`.

---

## 5. L3: TCP fingerprints describe the nearest TCP stack
- Mac lab, offload on vs off (MTU 1500): 1 frame of 1586 B vs 2 frames (1514 + 138 B); JA4 the same.
- SYN-ACK seen in the container: MSS 65495, TTL 63. Impossible on a 1500-byte path; made by Docker's network proxy.
- Windows lab, same connection at two capture points:

| Client SYN | Inside container | On Wi-Fi card |
|---|---|---|
| TTL | 64 | 128 |
| Window | 64240 | 65535 |
| Window scale | 10 | 8 |
| MSS | 1460 | 1460 |
| TCP timestamps | yes | no |

- Different ISN: Windows opened a new TCP connection. A Linux VM behind normal NAT kept its values (only TTL 64 to 63).
- A NAT keeps the TCP fingerprint; a proxy replaces it. JA4T on the Wi-Fi describes Windows, not the Linux container.

**Say:** Data in `docs/tests/T3_vantage_offload.md` and `results/l3_paired_batch/`.

---

## 6. Keys, post-quantum and ECH: what an observer still sees
- **L2:** JA4X + JA4H 0 without keys, 5 with keys (4 certificates + 1 HTTP request). Everything after the ServerHello is encrypted in TLS 1.3; a real tap only gets JA4 and JA4S.
- **L4:** ClientHello 508 B (X25519) vs 1511 B (X25519MLKEM768); key share 32 B vs 1216 B. JA4 changes (14 to 12 extensions) through side effects: no `ec_point_formats`, no padding extension.
- **L7:** ECH on: SNI `cloudflare-ech.com`, but plain DNS still asks for `crypto.cloudflare.com`. DoH did not work on campus, so that case is not measured.

---

## 7. Track 2: our own QUIC Initial extractor in C++20
- Steps: read pcap (Ethernet, IP, UDP) -> QUIC header (RFC 9000 §17.2) -> Initial keys (RFC 9001 §5.2) -> decrypt (AES-128-GCM) -> join CRYPTO by offset -> ClientHello, same bytes as TShark.
- Connection ID switch: the first Initial uses ID A and keys come from A; the server picks ID B; the client's next Initials carry B but keys still come from A. A stateless extractor fails on every packet with B; our stateful mode remembers A per UDP 4-tuple.

| | curl | Chromium |
|---|---|---|
| Client Initial packets | 20 | 16 |
| Decrypted, stateless | 10 | 10 |
| Decrypted, stateful | 20 | 16 |
| ClientHellos = TShark (both modes) | 5/5 | 5/5 |
| Reversed order: stateless / stateful | 5/5 / 0/5 | 5/5 / 0/5 |

- TShark already handles the switch; our stateful mode now matches it. In our pcaps the later packets hold only ACK + PADDING, so the JA4 does not change. Reordering is a known weak point.

**Say:** Key derivation is checked against the RFC 9001 Appendix A vector. Data: `results/track2/verification-batch-20261105-105416/`.

---

## 8. What we take away
- Findings: QUIC does not stop fingerprinting (L1). A fingerprint depends on the tool version and on where you capture, not only on the client (L5, L3). Without keys you lose JA4X and JA4H; ECH without encrypted DNS still leaks the site name (L2, L7).
- Not covered: IPv6; one network, inside Docker; one site, three clients; QUIC Retry, migration, v2; stateful mode and reordering.
- Re-run: `make test` (CTest 1/1, pytest 52), `make check` (16 pcaps match SHA-256), `make lab-eval` (TShark + FoxIO on every pcap).

**Demo if asked:** `make test`; `./build/code/quic/src/quic-fingerprint --pcap captures/pcaps/quic_curl.pcap`; the TShark command in `results/track1/recheck-20261106.md` that counts 15 JA4s.
