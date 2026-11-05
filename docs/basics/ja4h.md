# JA4H — HTTP request fingerprint

**Maintainer/source:** FoxIO JA4+ ([v1.0.1 release](https://github.com/FoxIO-LLC/ja4/releases/tag/v1.0.1), [Python implementation](https://github.com/FoxIO-LLC/ja4/blob/v1.0.1/python/ja4h.py)); vendor/community construction, not an IETF standard. **Source tag commit:** `896b951e438c2979e0ef077a94ad390b1c973c23`. **Checked:** 5 November 2026.

| Aspect | Definition / decision |
|---|---|
| Message and direction | HTTP request/application data. The cited implementation covers HTTP/1.x and HTTP/2; HTTP/3 requires a QUIC/HTTP3-capable decoder. |
| Input components | Request method, HTTP version, request-header names and selected language/referer/cookie indicators; cookie-related fields are handled according to the specific implementation. |
| Canonicalization | Structured output with compact hashes. The cited source sorts cookie field names for its normalized component; raw/ordered variants may also be emitted. Pin exact version and avoid retaining sensitive header/cookie values unnecessarily. |
| Visibility | Plain HTTP is readable. HTTPS HTTP/1.1 and HTTP/2 require TLS decryption or trusted endpoint/proxy logs; HTTP/3 requires suitable QUIC 1-RTT secrets or endpoint logs. QUIC Initial decryption alone is insufficient. |
| Protocol references | HTTP semantics: [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html); HTTP/2: [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html); HTTP/3: [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html); cookies: [RFC 6265](https://www.rfc-editor.org/rfc/rfc6265.html). These do not define JA4H. |
| Interpretation limit | Describes a request pattern, not a TLS stack, user identity, or destination identity. It is request/session/content dependent and may reveal sensitive data if raw headers are retained. |
| Project evidence | The team-reported L2 TLS 1.3 sample yielded zero JA4X/JA4H records without keys and one JA4H output with keys. The key log is intentionally absent; this is a one-sample visibility result, not a general claim. |
