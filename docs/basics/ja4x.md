# JA4X — X.509 certificate fingerprint

**Maintainer/source:** FoxIO JA4+ ([v1.0.1 release](https://github.com/FoxIO-LLC/ja4/releases/tag/v1.0.1), [Python implementation](https://github.com/FoxIO-LLC/ja4/blob/v1.0.1/python/ja4x.py)); vendor/community construction, not an IETF standard. **Source tag commit:** `896b951e438c2979e0ef077a94ad390b1c973c23`. **Checked:** 5 November 2026.

| Aspect | Definition / decision |
|---|---|
| Object and direction | X.509 certificate(s) in a TLS certificate chain; certificate, not ClientHello, layer. |
| Input components | Issuer/subject distinguished-name material and certificate extension OIDs in the cited implementation. Chain position and parsing affect results. |
| Canonicalization | Structured components include issuer/subject-derived material and truncated SHA-256-derived extension-OID data. Exact encoding and chain handling are implementation-version-specific. |
| Visibility | TLS 1.2 certificates are commonly visible in the handshake. TLS 1.3 certificates are encrypted after ServerHello and normally require traffic secrets or trusted endpoint/server logs. QUIC Initial decryption alone is insufficient for later certificate messages. |
| Protocol references | X.509: [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280.html); TLS Certificate message and encrypted handshake: [RFC 8446 §4.4.2](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.4.2). These do not define JA4X. |
| Interpretation limit | Describes observed certificate material, not necessarily a unique server or client. Shared/CDN certificates, renewal, chain differences, and interception affect values. Do not retain private key logs in the repository. |
| Project evidence | The team-reported L2 TLS 1.3 sample yielded zero JA4X/JA4H records without keys and four JA4X certificate-chain entries with keys. The key log is intentionally absent; this is not independently reproducible from this repository. |
