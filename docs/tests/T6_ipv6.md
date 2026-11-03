# T6: Does IPv6 change the fingerprint? (L6)

**One line:** the same curl connects over IPv4 and over IPv6, and we compare fingerprints.

## What is being done
- `curl -4` to `https://www.cloudflare.com/cdn-cgi/trace`, **3 times**.
- `curl -6` to the same URL, **3 times**.

## What is being tested
Does JA4 stay the same across IP versions, and which TCP/IP-level values change?

## Why
- Sir: *"how IPv6 comes right now… are they going to work, potentially the fingerprinting approach completely changes."*
- JA4 has no IP field, so we expect it to stay the same. But:
  - the IPv6 header is 40 bytes instead of 20, so MSS is typically 1440 instead of 1460, which changes JA4T
  - IPv6 privacy addresses rotate (RFC 8981 §3.3), which breaks IP-based attribution
  - IPv6 has a different header chain (RFC 8200 §4)

## Control
The same curl, the same server, back to back; only `-4` / `-6`.

## Commands
```sh
make lab-capture CAPTURE_ID=tls_ipv4
make lab-capture CAPTURE_ID=tls_ipv6
make lab-eval
```

## What we saw
- IPv4: 3 hellos, JA4 `t13d3013h2_1d37bd780c83_8537cf56674e`.
- IPv6: **empty capture.** Neither the container nor the Mac has a global IPv6 address on the campus network; `curl -6` fails.

## Status: NOT measured

The committed `tls_ipv6.pcap` is a 24-byte PCAP header with **zero packet records**. The imported source summary had `tools_agree: true` because two empty result sets compared equal; the audited `results/summary.*` marks this as not comparable. No IPv6 fingerprint result is claimed. To retry on a network with IPv6, explicitly run `make lab-capture CAPTURE_ID=tls_ipv6` and then `make lab-eval`.
