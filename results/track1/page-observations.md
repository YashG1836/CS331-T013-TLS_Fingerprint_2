# Selected ECH page observations (team-supplied)

The following values were transcribed from Yash's saved `tls_ech_off_page.txt` and `tls_ech_on_page.txt` outputs. The original page dumps were not imported because they also contain workstation/network identifiers and dynamic response details.

| Capture | Reported page field | Observation |
|---|---|---|
| `tls_ech_off` | `h` | `crypto.cloudflare.com` |
| `tls_ech_off` | `sni` | `plaintext` |
| `tls_ech_on` | `h` | `crypto.cloudflare.com` |
| `tls_ech_on` | `sni` | `encrypted` |
| `tls_ech_doh` | page output | Empty; target page load is not evidenced by a saved response. |

These are team-supplied page outputs, not rerun or independently authenticated here. The summary's 12 ClientHello rows for `tls_ech_doh` are not treated as proof that the intended page loaded; Chromium may have generated background handshakes. The DoH arm remains incomplete.
