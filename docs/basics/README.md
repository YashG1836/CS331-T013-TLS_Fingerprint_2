# Fingerprint field cards

These cards expand the comparative survey in [`../landscape.md`](../landscape.md). JA3/JA4 names and normalization are implementation-defined constructions, not IETF fingerprint standards. The RFC references below define wire fields, not the fingerprint algorithms.

| Card | Layer / message | Primary implementation reference |
|---|---|---|
| [JA3](ja3.md) | Client TLS ClientHello | Salesforce JA3 repository |
| [JA3S](ja3s.md) | Server TLS ServerHello | Salesforce JA3 repository |
| [JA4](ja4.md) | Client TLS/QUIC ClientHello | FoxIO JA4+ v1.0.1 |
| [JA4S](ja4s.md) | Server TLS/QUIC ServerHello | FoxIO JA4+ v1.0.1 |
| [JA4T](ja4t.md) | Client TCP SYN | FoxIO JA4+ v1.0.1 |
| [JA4X](ja4x.md) | X.509 certificate | FoxIO JA4+ v1.0.1 |
| [JA4H](ja4h.md) | HTTP request | FoxIO JA4+ v1.0.1 |

**Checked:** 5 November 2026 against the source links in `docs/landscape.md`. This is a concise technical reference, not a systematic literature review. Pin tool/source versions before comparing output; the project’s WSL and Docker lab toolchains differ. Do not interpret a fingerprint as a unique host, user, application, or origin identity.
