# T7: What hides the website name: ECH, encrypted DNS? (L7)

**One line:** Chromium visits the same site three ways (ECH off, ECH on, ECH + encrypted DNS) while we capture both TLS and DNS, and check where the site name is still visible.

## What is being done
- Chromium opens `https://crypto.cloudflare.com/cdn-cgi/trace`. That page reports back `sni=plaintext` or `sni=encrypted`, which is Cloudflare's own confirmation.
- Three runs:
  1. **ECH off:** Chrome policy `EncryptedClientHelloEnabled=false` (`captures/config/ech_off_policy.json`)
  2. **ECH on:** Chromium default
  3. **ECH + DoH:** DNS-over-HTTPS to Cloudflare (`captures/config/doh_policy.json`)
- Capture filter: `tcp port 443 or port 53`, so we see TLS **and** plain DNS.

## What is being tested
1. Is the real site name visible in the TLS SNI?
2. Is it visible in DNS?
3. Does JA4 change when ECH is on?

## Why
- Sir and the phase 1 questions: "SNI?", "eSNI?". SNI (RFC 6066 §3) sends the site name in plaintext, and attribution ("which site is this app using") depends on it.
- **ECH** (draft-ietf-tls-esni) encrypts the real ClientHello with a key published in DNS (HTTPS record, RFC 9460). Outside it shows only a shared `public_name`.
- But DNS (RFC 1035) is plaintext unless you use DoH (RFC 8484).

## Control
Same browser, page and network. Only the ECH/DNS setting changes.

## Commands
```sh
make lab-capture CAPTURE_ID=tls_ech_off
make lab-capture CAPTURE_ID=tls_ech_on
make lab-capture CAPTURE_ID=tls_ech_doh
make lab-eval
cat results/track1/page-observations.md
```

## What we saw
| run | SNI on the wire | page says | DNS shows `crypto.cloudflare.com`? | JA4 (`ja4-main`) |
|---|---|---|---|---|
| ECH off | `crypto.cloudflare.com` | `sni=plaintext` | yes | `t13d1516h2_8daaf6152771_447d952d5833` |
| ECH on | `cloudflare-ech.com` | `sni=encrypted` | **yes** | `t13d1517h2_8daaf6152771_cb7bf5808d99` |
| ECH + DoH | - | page didn't load | - | - |

- ECH adds one extension (0xfe0d), so JA4 goes from 16 to 17 extensions.
- DNS check, from the pcaps ([`results/track1/recheck-20261106.md`](../../results/track1/recheck-20261106.md)): with ECH on, the SNI is `cloudflare-ech.com` (2 hellos), but plain DNS asks for `crypto.cloudflare.com` (2 queries).
- **DoH run:** not a result. All 12 ClientHellos go to `cloudflare-dns.com` (the DoH server), that name is itself looked up over plain DNS, and the target page output is empty. On the campus network the DoH connection failed with a certificate error, so the page never loaded.

## What it means
- ECH hides the name from TLS, but **plain DNS still gives it away**. You need ECH **and** working encrypted DNS.
- JA4 changes when ECH is on (one more extension, 0xfe0d), so ECH also changes the browser's fingerprint.

## What it does NOT prove
- The full ECH + DoH case (blocked here). Repeat on a network that allows DoH.
- One site (Cloudflare) and one browser.
