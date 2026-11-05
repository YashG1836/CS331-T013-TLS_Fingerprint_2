# JA4S — server TLS/QUIC fingerprint

**Maintainer/source:** FoxIO JA4+ ([v1.0.1 release](https://github.com/FoxIO-LLC/ja4/releases/tag/v1.0.1), [technical details](https://github.com/FoxIO-LLC/ja4/blob/v1.0.1/technical_details/README.md)); vendor/community algorithm, not an IETF standard. **Source tag commit:** `896b951e438c2979e0ef077a94ad390b1c973c23`. **Checked:** 5 November 2026.

| Aspect | Definition / decision |
|---|---|
| Message and direction | Server `ServerHello` response on the observed TLS or QUIC-TLS leg. |
| Input components | Transport indicator, TLS version, extension count, ALPN summary, selected cipher, and ServerHello extension types. |
| Canonicalization | Structured output; the cited v1.0.1 implementation hashes the server extension list in observed order and its source comment specifies GREASE inclusion. Do not assume client JA4 sorting/filtering rules apply. |
| Visibility | ServerHello is generally visible in a complete TLS 1.2/1.3 capture. Later TLS 1.3 certificate and application messages are encrypted. QUIC carries the TLS handshake in protected CRYPTO frames. |
| Protocol references | ServerHello: [RFC 5246 §7.4.1.3](https://www.rfc-editor.org/rfc/rfc5246.html#section-7.4.1.3), [RFC 8446 §4.1.3](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.1.3); ALPN: [RFC 7301](https://www.rfc-editor.org/rfc/rfc7301.html); GREASE: [RFC 8701](https://www.rfc-editor.org/rfc/rfc8701.html). These do not define JA4S. |
| Interpretation limit | The result depends on negotiation and the server response on that leg. It is not a full server-stack identity or proof of the origin behind a TLS-terminating intermediary. |
| Project status | No custom JA4S calculation is implemented or claimed. Record exact reference tool/version for any future measurement. |
