# Limitation ledger

One line per limitation. Details, commands and "what it does NOT prove" are in the linked test file.
Track 1 numbers come from the committed pcaps (`results/summary.md`, re-checked in [`results/track1/recheck-20261106.md`](results/track1/recheck-20261106.md)).
Track 2 numbers come from the WSL batch `results/track2/verification-batch-20261105-105416/`.

| ID | Question | Test | Main number | Status |
|---|---|---|---|---|
| L1 | Can real tools read the QUIC ClientHello? | [T1](docs/tests/T1_quic.md) | TShark and FoxIO: 5/5 hellos for curl and Chromium (Chromium's hello is in 21 CRYPTO pieces) | Our guess was wrong: they can |
| L2 | Which fingerprints need TLS keys? | [T2](docs/tests/T2_keys.md) | JA4X + JA4H: 0 without keys, 5 with keys (one TLS 1.3 session) | Confirmed |
| L3 | Does the capture point change what we see? | [T3](docs/tests/T3_vantage_offload.md) | Offload on: hello in 1 frame of 1586 B; off: 1514 + 138 B. SYN-ACK MSS 65495 came from Docker's proxy. On Windows the container's SYN leaves the Wi-Fi with Windows values (TTL 128, wscale 8) | Confirmed in our two labs |
| L4 | Does a post-quantum key share change the hello? | [T4](docs/tests/T4_post_quantum.md) | Hello 508 B (X25519) vs 1511 B (X25519MLKEM768); JA4 14 vs 12 extensions | Confirmed, via side effects |
| L5 | Is one browser one fingerprint? | [T5](docs/tests/T5_stability.md) | Chromium, 50 hellos: 50 JA3; JA4 = 15 with TShark 4.6.8 / FoxIO v0.18.6, but 1 with FoxIO v1.0.1 | Confirmed: depends on tool version |
| L6 | IPv4 vs IPv6 | [T6](docs/tests/T6_ipv6.md) | IPv6 pcap has 0 packets (no IPv6 route on campus or WSL) | Not measured |
| L7 | Does ECH hide the site? | [T7](docs/tests/T7_ech_dns.md) | ECH on: SNI `cloudflare-ech.com`, but plain DNS still asks for `crypto.cloudflare.com`. DoH run did not load | Confirmed; DoH not measured |

Certificate compression / abridged certificates: only mentioned, not measured.

## Track 2: our C++ QUIC Initial extractor

Same two QUIC pcaps, compared with TShark 4.6.4 on the same file.

| | curl | Chromium |
|---|---|---|
| client Initial packets | 20 | 16 |
| decrypted, keys from each packet's own DCID (stateless) | 10 | 10 |
| decrypted, keys from the connection's first DCID (stateful) | **20** | **16** |
| complete ClientHellos, both modes | 5/5, same bytes as TShark | 5/5, same bytes as TShark |

- The failing packets are the client packets sent after the server picked its own connection ID (RFC 9000 §7.2). RFC 9001 §5.2 says their keys still come from the first DCID.
- In these pcaps those packets carry only ACK and PADDING, so the ClientHello and JA4 are the same in both modes. TShark already handles this case; the stateful mode makes our extractor match it.
- Damaged copies (stateless mode): 54/54 hellos equal to TShark across 6 cases × 2 pcaps.
- Damaged copies (stateful mode): reverse order 0/5 and shuffle 4/5 per pcap. If a later packet comes first, the stateful mode takes the wrong connection ID as the key source. Stateless mode does not have this problem.

## Facts about the tools
- FoxIO tag v0.18.6 reports `ja4 0.18.5`; tag v1.0.1 reports `ja4 0.18.6` (`rust/Cargo.toml` not updated).
- FoxIO ja4 reads packets through TShark (`rtshark`), so TShark and FoxIO agreeing is two calculators on one packet parser.
- JA4T: not in TShark 4.4.19 or FoxIO v0.18.6; FoxIO v1.0.1 has it.

## Lab setup
- Track 1 captures: Docker (`cn-lab`, Debian) on a MacBook (aarch64), campus network. Versions: `results/versions.txt`.
- Track 2 batch and the L3 paired run: Windows 11 + WSL2 Ubuntu (TShark 4.6.4, GCC 15.2.0, OpenSSL 3.5.5). Versions: `environment.txt` in each batch folder.
