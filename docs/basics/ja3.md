# JA3 — client TLS fingerprint

**Maintainer/source:** Salesforce JA3 repository ([source](https://github.com/salesforce/ja3)); formula is community/vendor-defined, not an IETF standard. **Checked:** 5 November 2026. No source release is pinned by this project card; record the exact revision/executable for any experiment.

| Aspect | Definition / decision |
|---|---|
| Message and direction | Client TLS `ClientHello`, ordinarily carried over TCP; dissectors may also decode TLS handshake messages transported by QUIC. |
| Input components | Legacy version; cipher-suite vector; extension-type vector; supported-groups vector; EC point-format vector. |
| Canonical string | Comma-separated components; members of vector fields are hyphen-separated. Selected list order is retained. GREASE values are removed. |
| Output | MD5 digest of the canonical string (32 hexadecimal characters). Treat it as a compact label, not an identity/security hash. |
| Visibility | An ordinary ClientHello is generally visible without TLS secrets. For ECH, passive observers see the outer ClientHello, not the encrypted inner ClientHello. QUIC v1 Initial is a special publicly decryptable packet-protection layer under RFC 9001. |
| Protocol references | TLS ClientHello: [RFC 5246 §§7.4.1.2–7.4.1.3](https://www.rfc-editor.org/rfc/rfc5246.html#section-7.4.1.2), [RFC 8446 §§4.1.2–4.1.3](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.1.2); supported groups: [RFC 8422 §5.1](https://www.rfc-editor.org/rfc/rfc8422.html#section-5.1); GREASE: [RFC 8701](https://www.rfc-editor.org/rfc/rfc8701.html). These define fields/behavior, not JA3. |
| Interpretation limit | Extension-order randomization can change JA3 for one client; different clients may collide/share values. It describes the observed ClientHello on a leg, not a person, executable, or ultimate destination. |
