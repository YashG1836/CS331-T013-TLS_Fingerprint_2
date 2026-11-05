# T2: Which fingerprints work without TLS keys? (L2)

**One line:** make one TLS 1.3 connection while saving its keys, then run ja4 on the same pcap twice, once without the keys and once with them.

## What is being done
- curl makes **1** TLS 1.3 + HTTP/1.1 request to `https://www.cloudflare.com/cdn-cgi/trace` with `SSLKEYLOGFILE` set, so curl writes its session keys to `captures/keylogs/tls_keylog_curl.keylog`.
- `ja4 pcap` (no keys) vs `ja4 --keylog-file keys pcap` (with keys), on the **same** pcap.

## What is being tested
How many JA4X (certificate) and JA4H (HTTP) fingerprints come out without keys vs with keys.

## Why
- A real network tap (firewall, IDS) **never has the keys**. FoxIO advertises JA4X and JA4H as fingerprints, so we check whether a tap can actually get them.
- In TLS 1.3 everything after ServerHello is encrypted, **including the certificate** (RFC 8446 §2, §4.4.2). The HTTP request is inside TLS too.

## Control / what stays the same
Exactly the same bytes (one pcap). The only change is: keys given or not.

## Commands
```sh
make lab-capture CAPTURE_ID=tls_keylog_curl
make lab-eval      # column ja4x_ja4h_no_keys vs ja4x_ja4h_with_keys
```

## Expected
0 without keys, more than 0 with keys.

## What we saw
| | JA4X + JA4H |
|---|---|
| no keys | **0** |
| with keys | **5** (4 JA4X, one per certificate in the chain, + 1 JA4H) |

JA4 and JA4S were present in both runs (they come from plaintext hellos).

## What it means
- On TLS 1.3, JA4X and JA4H are **lab-only** fingerprints. A passive observer gets JA4 + JA4S (+ JA4T, if a tool had it).

## What it does NOT prove
- TLS 1.2 servers still send the certificate in plaintext; we didn't test TLS 1.2.
- The key log is intentionally not committed. The imported summary reports 5 JA4X/JA4H records with keys, but the key-log file is absent, so that arm cannot be regenerated from the repository. Never commit public-session or personal key logs.
