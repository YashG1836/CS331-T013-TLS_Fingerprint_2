# JA4 — client TLS/QUIC fingerprint

**Maintainer/source:** FoxIO JA4+ ([v1.0.1 release](https://github.com/FoxIO-LLC/ja4/releases/tag/v1.0.1), [technical details](https://github.com/FoxIO-LLC/ja4/blob/v1.0.1/technical_details/README.md), [Python source](https://github.com/FoxIO-LLC/ja4/blob/v1.0.1/python/ja4.py)); vendor/community algorithm, not an IETF standard. **Source tag commit:** `896b951e438c2979e0ef077a94ad390b1c973c23`. **Checked:** 5 November 2026.

| Aspect | Definition / decision |
|---|---|
| Message and direction | Client `ClientHello`; supports TCP-TLS and QUIC-TLS when the implementation can decode the handshake. |
| Input components | Transport indicator, TLS version, SNI presence, cipher count, extension count, ALPN summary, cipher-suite list, extension-type list, and signature-algorithm values. |
| Canonicalization | Structured `a_b_c` form. In v1.0.1, selected cipher and extension lists are sorted for hashed components; GREASE is filtered from the client extension count/lists. Signature algorithms contribute to the extension-derived component. Exact behavior is release-specific. |
| Output | Prefix plus compact SHA-256-derived components. Compare parsed fields as well as final hashes when validating an implementation. |
| Visibility | Ordinary ClientHello fields are usually visible without TLS secrets. ECH hides ClientHelloInner. QUIC v1 Initial ClientHello can be recovered from public Initial inputs under RFC 9001; later handshake/application data require the appropriate secrets. |
| Protocol references | ClientHello: [RFC 8446 §§4.1.2–4.1.3](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.1.2); SNI: [RFC 6066 §3](https://www.rfc-editor.org/rfc/rfc6066.html#section-3); ALPN: [RFC 7301](https://www.rfc-editor.org/rfc/rfc7301.html); signature algorithms: [RFC 8446 §4.2.3](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.2.3); GREASE: [RFC 8701](https://www.rfc-editor.org/rfc/rfc8701.html); QUIC TLS: [RFC 9001](https://www.rfc-editor.org/rfc/rfc9001.html). |
| Interpretation limit | Sorting reduces some order sensitivity but does not make JA4 invariant or unique. It describes fields on the captured leg; it is not proof of a user, application, or ultimate origin. Do not emit custom QUIC JA4 until fields and transport marking match a pinned reference. |
| Project status | The current C++ extractor does **not** calculate JA4. TShark and FoxIO share a dissection dependency in the Rust CLI path, so they are not fully independent decoders. |
