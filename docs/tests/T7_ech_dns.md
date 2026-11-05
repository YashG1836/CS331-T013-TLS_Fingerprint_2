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
- **DoH run:** the imported explanation reports a certificate error while reaching `cloudflare-dns.com`, but the committed page output is empty and the specific certificate details are not preserved. The target page load is therefore unverified. The summary has 12 ClientHello rows for this pcap; these may be Chromium background connections and are not evidence the intended ECH+DoH test succeeded. See `results/track1/page-observations.md`.

## What it means
- ECH hides the name from TLS, but **plain DNS still gives it away**. You need ECH **and** encrypted DNS.
- The two saved page outputs support an ECH-off/on SNI difference for this run. They do not validate the ECH+DoH arm. The team's explanation that campus DoH was blocked remains a reported cause, not an independently reproduced result.
- JA4 fingerprinting and site-name attribution are distinct observations; no broad browser-identity guarantee is inferred from this one capture set.

## What it does NOT prove
- The full ECH + DoH case (blocked here). Repeat on a network that allows DoH.
- One site (Cloudflare) and one browser.
