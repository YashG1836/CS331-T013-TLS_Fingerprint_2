# T5: Is one client = one fingerprint? (L5)

**One line:** open many fresh connections from the same client and count how many different fingerprints come out; do the same for two apps that share one TLS library.

## What is being done
- Chromium 156: 10 page loads, giving **50 ClientHellos** (the page plus Chromium's own background connections).
- curl: **10** connections. Python `urllib`: **10** connections. Both use the same OpenSSL 3.5.7.
- We count distinct JA3 and JA4 per client, with:
  - our lab pin: FoxIO tag v0.18.6 and tshark 4.4.19
  - FoxIO `main` (commit c6469a7), built as `ja4-main`
  - later re-check: FoxIO tag v1.0.1 and TShark 4.6.8

## What is being tested
1. **Stability:** does the same client always get the same fingerprint?
2. **Collision:** do two apps on the same library get the same fingerprint?

## Why
- Sir: *"the same application cannot have different hash? … it can"*, and *"will it work tomorrow?"*.
- A blocklist (sir's example: block Firefox, allow Chrome) only works if one client = one fingerprint.
- Phase 1 bug: our detector flagged **real Chrome** as fake because JA3 changed. Chrome shuffles extensions (RFC 8446 §4.1.2 allows any order).
- GREASE (RFC 8701) = random reserved values that clients insert; fingerprints must ignore them.

## Control / what stays the same
Same machine, same server, fresh browser profile each time; curl and Python are the "simple client" controls.

## Commands
```sh
make lab-capture CAPTURE_ID=tls_chromium_repeat
make lab-capture CAPTURE_ID=tls_curl_repeat
make lab-capture CAPTURE_ID=tls_python_repeat
make lab-eval
# extra check with the newest Wireshark on the Mac:
tshark -r captures/pcaps/tls_chromium_repeat.pcap -Y "tls.handshake.type==1" -T fields -e tls.handshake.ja4 | sort -u | wc -l
# how many different first signature algorithms (GREASE values) Chromium used -> 15:
tshark -r captures/pcaps/tls_chromium_repeat.pcap -Y "tls.handshake.type==1" -T fields -e tls.handshake.ja4_r | cut -d_ -f4 | cut -d, -f1 | sort -u | wc -l
```

## Expected
JA3: many values for Chromium (shuffling). JA4: 1 value per client (it sorts).

## What we saw
| client | hellos | distinct JA3 | distinct JA4 (TShark 4.4.19, FoxIO v0.18.6) | distinct JA4 (FoxIO main) |
|---|---|---|---|---|
| Chromium 156 | 50 | **50** | **15** | **1** |
| curl | 10 | 1 | 1 | 1 |
| Python | 10 | 1 | 1 | 1 |

- Re-checked on 6 Nov with more tool versions on the same pcap ([`results/track1/recheck-20261106.md`](../../results/track1/recheck-20261106.md)):

| tool | distinct JA4 for Chromium's 50 hellos |
|---|---|
| TShark 4.4.19 (lab) and TShark 4.6.8 (Mac) | 15 |
| FoxIO tag v0.18.6 (our lab pin) | 15 |
| FoxIO tag v1.0.1 (31 Aug 2026) and FoxIO main | **1** |

- **Why 15:** Chromium puts a random GREASE value first in `signature_algorithms`. The 50 hellos use 15 different GREASE values there (`0a0a` ... `fafa`), one per JA4. FoxIO's spec says to ignore GREASE; FoxIO fixed this in commit d66336e ("ignore grease in sigalgs"), first released in v1.0.1. TShark 4.6.8 still counts it.
- **Collision:** curl and Python share **JA4 part b** (`1d37bd780c83`, the cipher list from OpenSSL), but differ in parts a and c (HTTP/2 vs HTTP/1.1, 13 vs 14 extensions). So they partly collide, not fully.

## What it means
- JA3 is not usable for Chromium: every connection gave a new JA3.
- The JA4 of one browser depends on **which tool and version computed it**: 15 values with TShark 4.6.8 or FoxIO v0.18.6, 1 value with FoxIO v1.0.1. A JA4 list made with one tool will miss most Chromium connections seen by the other.
- So a JA4 database must record the tool and version, and fingerprints should be recomputed after a tool update.
- Phase 1's documented Chrome JA4 (`..._541cd5a3d78e`) is one of these 15.

## What it does NOT prove
- One Chromium version, one OS. Firefox not tested. The 50 hellos include Chromium's background connections.
- It is not a new bug: FoxIO already fixed it. What we show is that tools in use today (TShark stable, older FoxIO) still give different answers.
