# T1: Can the real tools fingerprint QUIC? (L1)

**One line:** load the same small page over QUIC with two different real clients and see if tshark and ja4 recover the ClientHello.

## What is being done
- Chromium 156 loads `https://cloudflare-quic.com/cdn-cgi/trace` over QUIC (HTTP/3), **5 times**.
- curl 8.14.1 (HTTP/3) loads the same page, **5 times**.
- tcpdump records UDP port 443. Then tshark and ja4 read the pcap.

## What is being tested
1. Does each tool find **every** QUIC ClientHello? (5 of 5?)
2. Do the two tools give the **same** JA4?
3. Do they still work when the ClientHello is split into many pieces?

## Why
- Sir: "if I have to give you an objective, I would say, do QUIC."
- In QUIC the ClientHello is **inside encrypted Initial packets**, not in plaintext like TCP. A tool must:
  1. derive the Initial keys from a public salt + the Destination Connection ID (RFC 9001 §5.2)
  2. remove header protection (RFC 9001 §5.4)
  3. decrypt (AEAD)
  4. put CRYPTO frames back together by offset (RFC 9000 §19.6)
- Our hypothesis (from the plan): tools may fail here.

## Control / what stays the same
Same server, same page, same network; only the client changes. TCP tests (T5) are the "normal" comparison.

## Commands
```sh
make lab-capture CAPTURE_ID=quic_chromium
make lab-capture CAPTURE_ID=quic_curl
make lab-eval
```

## Expected (hypothesis written before)
At least one tool misses or mis-builds the QUIC ClientHello.

## What we saw (results/summary.md)
| capture | hellos (tshark / ja4) | biggest hello | pieces | JA4 same in both tools? |
|---|---|---|---|---|
| quic_chromium | 5 / 5 | 1887 bytes | **21 CRYPTO fragments** | yes |
| quic_curl | 5 / 5 | 1505 bytes | 1 | yes |

- The server chose group 4588 (post-quantum hybrid) in both.
- Chromium used **ECH inside QUIC** on its own: the outer name was `cloudflare-ech.com`.

## What it means
- **Hypothesis wrong.** Wireshark 4.4 + FoxIO 0.18 handle normal, complete QUIC captures, even Chromium's deliberately fragmented hello. A negative result is still a result.
- QUIC Initial encryption does not hide the ClientHello: the keys come from the connection ID, which anyone can read (RFC 9001 §5.2).
- Track 2: our own C++ extractor gets the same 5 ClientHellos, byte for byte equal to TShark, on these two pcaps and on 5 damaged copies of each (54/54 hellos, `results/track2/verification-batch-20261104-201936/`). See `docs/quic/implementation-status.md`.

## What it does NOT prove (open → Track 2)
- **Connection migration** (sir's point): after the client changes network, the new path has no ClientHello at all (RFC 9000 §9). Not tested.
- Capture that misses the first packet, Retry, QUIC v2 (RFC 9369): not tested.
- Only 2 clients and 1 server.
