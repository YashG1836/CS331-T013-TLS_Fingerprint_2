# Our tests: index

Phase 1 problem: tests looked random (one capture per client, no clear question). This time **every test answers one question and changes only one thing.**

## How every test is built
1. **Question:** one sentence, written *before* capturing.
2. **One variable changes:** everything else stays the same (same client, same server, same tools).
3. **Control:** the "normal" case next to the changed case, so a difference means something.
4. **Real tools only:** tshark (Wireshark, C) and FoxIO ja4 (Rust) read the capture. We don't compute fingerprints.
5. **The imported numbers are in `results/summary.md`**; the unchanged source is preserved in `results/imported/`. `make lab-eval` writes a fresh comparison under `results/reproduced/`; tool-version differences can change outputs.
6. **Each file says what the test does NOT prove.**

The committed summaries are teammate-supplied outputs, not rerun in this checkout. FoxIO's Rust CLI uses TShark, so agreement is not independent packet decoding. The audited summary marks the empty IPv6 capture not comparable; see [`docs/track1-evidence-audit.md`](../track1-evidence-audit.md).

## The tests

| File | Question in one line | Changed variable | Result |
|---|---|---|---|
| [T0_lab_checks.md](T0_lab_checks.md) | Can we trust our lab and scripts? | - | passed |
| [T1_quic.md](T1_quic.md) | Can the reference tools fingerprint QUIC? | TCP → QUIC, two clients | imported results: 5/5 each; C++ not yet tested |
| [T2_keys.md](T2_keys.md) | Which fingerprints work without TLS keys? | keys given / not given | imported output: 0 vs 5; key log omitted |
| [T3_vantage_offload.md](T3_vantage_offload.md) | Does *where/how* we capture change what we see? | offload on / off | imported metrics differ; narrative mismatch open |
| [T4_post_quantum.md](T4_post_quantum.md) | What does a post-quantum key share change? | PQ group on / off | imported size/group/JA4 observations |
| [T5_stability.md](T5_stability.md) | Is one client = one fingerprint? | same client, 10 repeats | imported: Chromium 15 vs `ja4-main` 1 |
| [T6_ipv6.md](T6_ipv6.md) | Does IPv6 change the fingerprint? | IPv4 / IPv6 | not measured: zero-packet capture |
| [T7_ech_dns.md](T7_ech_dns.md) | What hides the website name: ECH, DNS? | ECH off / on / + DoH | ECH page outputs imported; DoH arm incomplete |

Not a test: **L8 certificate abridging**. It isn't deployed, so there's nothing real to capture (see LEDGER.md).

## Run them
```sh
make lab-image                          # once
make lab-capture CAPTURE_ID=tls_pq_on
make lab-capture CAPTURE_ID=tls_pq_off   # re-make one test's captures (needs internet)
make lab-eval                           # recompute every number from the committed pcaps (no internet needed)
```
