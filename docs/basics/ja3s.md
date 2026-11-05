# JA3S — server TLS fingerprint

**Maintainer/source:** Salesforce JA3 repository ([source](https://github.com/salesforce/ja3)); community/vendor-defined formula, not an IETF standard. **Checked:** 5 November 2026. No source release is pinned by this project card; record the exact revision/executable used.

| Aspect | Definition / decision |
|---|---|
| Message and direction | Server `ServerHello` on the observed TLS leg. |
| Input components | Negotiated TLS version, selected cipher suite, and ServerHello extension-type vector. |
| Canonicalization | Comma-separated values, extension types represented in observed order; GREASE values are filtered by the cited JA3 implementation. MD5 is applied to the canonical string. |
| Output | 32-character hexadecimal MD5 label. It is not a security property or unique server identity. |
| Visibility | ServerHello fields are ordinarily visible in TLS 1.2/1.3 when captured. Later TLS 1.3 handshake messages, including certificates, are encrypted after ServerHello. |
| Protocol references | ServerHello: [RFC 5246 §7.4.1.3](https://www.rfc-editor.org/rfc/rfc5246.html#section-7.4.1.3), [RFC 8446 §4.1.3](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.1.3); GREASE: [RFC 8701](https://www.rfc-editor.org/rfc/rfc8701.html). These do not define JA3S. |
| Interpretation limit | The result depends on the client offer, negotiated version/cipher, server configuration, and capture leg. A TLS-terminating intermediary may be the observed server; JA3S does not identify the ultimate origin behind it. |
