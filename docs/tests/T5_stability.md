# T5: Is one client = one fingerprint? (L5)

**One line:** open many fresh connections from the same client and count how many different fingerprints come out; do the same for two apps that share one TLS library.

## What is being done
- Chromium 156: 10 page loads, giving **50 ClientHellos** (the page plus Chromium's own background connections).
- curl: **10** connections. Python `urllib`: **10** connections. Both use the same OpenSSL 3.5.7.
- We count distinct JA3 and JA4 per client, with:
  - **released** tools: FoxIO v0.18.6 and tshark 4.4.19
  - FoxIO's **unreleased** `main` (commit c6469a7), built as `ja4-main`

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
| client | hellos | distinct JA3 | distinct JA4 (released tools) | distinct JA4 (`ja4-main`) |
|---|---|---|---|---|
| Chromium 156 | 50 | **50** | **15** | **1** |
| curl | 10 | 1 | 1 | 1 |
| Python | 10 | 1 | 1 | 1 |

- A separate teammate note says TShark 4.6.8 on macOS also returned **15**; that run is not represented in the committed Docker `results/versions.txt` or raw outputs.
- **Team's explanation for 15:** Chromium's `signature_algorithms` includes a GREASE value; the imported output reports 15 standard JA4 values versus 1 from FoxIO `ja4-main` commit `c6469a7b0dbf8fe963810162429fbfd9d1acc4d5`.
  - This is an imported tool-version comparison, not a result of our C++ parser. The supplied per-capture raw JSON does not include the `ja4-main` records, so the reported value of 1 cannot be recomputed from those raw files alone.
  - The claimed GREASE root cause and exact source behavior still need independent inspection and reproduction against the pinned source/tool builds. See `docs/track1-evidence-audit.md`.
- **Collision:** curl and Python share **JA4 part b** (`1d37bd780c83`, the cipher list from OpenSSL), but differ in parts a and c (HTTP/2 vs HTTP/1.1, 13 vs 14 extensions). So they partly collide, not fully.

## What it means
- In this 50-ClientHello sample, every reported JA3 differed; do not generalize that to every Chromium release or deployment.
- The imported released-tool output has 15 distinct JA4 values, versus 1 from the specified `ja4-main` commit. This sample suggests a release-specific stability issue; it does not establish that all JA4 blocklists fail or that 16 identities occurred.
- Phase 1's documented Chrome JA4 (`…_541cd5a3d78e`) is one of the imported values; this is a consistency clue, not independent confirmation.

## What it does NOT prove
- One Chromium version, one OS. Firefox not tested.
- The fix exists upstream, so this is a **deployment gap** (released vs unreleased), not a new discovery.
