# T4: What does a post-quantum key share change? (L4)

**One line:** the same curl connects 5 times offering only the post-quantum hybrid group, and 5 times offering only the classic group; compare size and fingerprints.

## What is being done
- `curl --curves X25519MLKEM768` (post-quantum hybrid), **5 times**.
- `curl --curves X25519` (classic), **5 times**.
- The server is the same; tshark and ja4 read both pcaps.

## What is being tested
1. How big is the ClientHello?
2. Which group did the server actually choose? (proof, not assumption)
3. Do JA3 / JA4 change, and why?

## Why
- Sir: *"Now we have PQC… nobody knows whether the fingerprint will work or not."*
- Post-quantum keys are large: X25519MLKEM768 adds about 1.2 KB to the `key_share` extension (RFC 8446 §4.2.8). The hello then doesn't fit in one packet.
- JA4 has **no field for groups**, so naively it "shouldn't change". We test that.

## Control / what stays the same
Same client binary, same server, same everything except the `--curves` option.

## Commands
```sh
make lab-capture CAPTURE_ID=tls_pq_on
make lab-capture CAPTURE_ID=tls_pq_off
make lab-eval
```

## Expected
Hello much bigger with PQ; JA3 changes (it includes groups); JA4 unchanged.

## What we saw
| | ClientHello | group chosen by server | JA4 |
|---|---|---|---|
| PQ on | **1511 bytes** | **4588** (0x11EC = X25519MLKEM768) | `t13d3012h2_1d37bd780c83_7f037f8d6676` |
| PQ off | **508 bytes** | **29** (x25519) | `t13d3014h2_1d37bd780c83_3eb322dd144c` |

The imported aggregate reports `pieces_max=1` with offload enabled and `2` with it disabled (T3). Do not describe one as a universal on-wire segment count; the captures are from inside Docker and the T3 narrative/aggregate frame-size values still need reconciliation.

**JA4 changed anyway** (12 vs 14 extensions), as the raw output `ja4_r` in `results/raw/` shows:
- PQ only: OpenSSL drops `ec_point_formats` (0x000b, RFC 8422 §5.1.2).
- Small classic hello (508 bytes): OpenSSL adds the `padding` extension (0x0015, RFC 7685), which it does for hellos of 256–511 bytes.

## What it means
- A crypto setting changes the fingerprint through **side effects**, not through the group field. A fingerprint database must be rebuilt when clients move to PQ.
- The hello crossing packet boundaries breaks anything that reads "one packet = one hello".

## What it does NOT prove
- Only OpenSSL/curl. Chromium also uses group 4588 by default (seen in T1/T5), but we didn't switch PQ off in Chromium.
