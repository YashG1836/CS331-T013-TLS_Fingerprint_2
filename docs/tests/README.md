# Our tests: index

Phase 1 problem: tests looked random (one capture per client, no clear question). This time **every test answers one question and changes only one thing.**

## How every test is built
1. **Question:** one sentence, written *before* capturing.
2. **One variable changes:** everything else stays the same (same client, same server, same tools).
3. **Control:** the "normal" case next to the changed case, so a difference means something.
4. **Real tools only:** tshark (Wireshark, C) and FoxIO ja4 (Rust) read the capture. We don't compute fingerprints.
5. **The numbers are in `results/summary.md`** (original copy in `results/imported/`). Numbers that the summary does not keep were re-checked with TShark and FoxIO in [`results/track1/recheck-20261106.md`](../../results/track1/recheck-20261106.md). `make lab-eval` writes a fresh run under `results/reproduced/`.
6. **Each file says what the test does NOT prove.**

FoxIO's Rust CLI uses TShark, so agreement is not independent packet decoding. The audited summary marks the empty IPv6 capture not comparable; see [`docs/track1-evidence-audit.md`](../track1-evidence-audit.md).

## The tests

| File | Question in one line | Changed variable | Result |
|---|---|---|---|
| [T0_lab_checks.md](T0_lab_checks.md) | Can we trust our lab and scripts? | - | passed |
| [T1_quic.md](T1_quic.md) | Can the reference tools fingerprint QUIC? | TCP → QUIC, two clients | 5/5 hellos in both tools; our C++ extractor gives the same bytes |
| [T2_keys.md](T2_keys.md) | Which fingerprints work without TLS keys? | keys given / not given | JA4X+JA4H: 0 without keys, 5 with keys |
| [T3_vantage_offload.md](T3_vantage_offload.md) | Does *where/how* we capture change what we see? | offload on / off | 1 frame (1586 B) vs 2 frames; SYN-ACK MSS 65495 from Docker proxy |
| [T4_post_quantum.md](T4_post_quantum.md) | What does a post-quantum key share change? | PQ group on / off | 508 B vs 1511 B; JA4 14 vs 12 extensions |
| [T5_stability.md](T5_stability.md) | Is one client = one fingerprint? | same client, 10 repeats | Chromium: 15 JA4s (TShark, FoxIO v0.18.6) vs 1 (FoxIO v1.0.1) |
| [T6_ipv6.md](T6_ipv6.md) | Does IPv6 change the fingerprint? | IPv4 / IPv6 | not measured: zero-packet capture |
| [T7_ech_dns.md](T7_ech_dns.md) | What hides the website name: ECH, DNS? | ECH off / on / + DoH | SNI hidden, DNS still shows the name; DoH run did not load |

Not a test: **L8 certificate abridging**. It isn't deployed, so there's nothing real to capture (see LEDGER.md).

## Run them
```sh
make lab-image                          # once
make lab-capture CAPTURE_ID=tls_pq_on
make lab-capture CAPTURE_ID=tls_pq_off   # re-make one test's captures (needs internet)
make lab-eval                           # recompute every number from the committed pcaps (no internet needed)
```
