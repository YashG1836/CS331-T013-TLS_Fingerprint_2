# JA4T — TCP SYN fingerprint

**Maintainer/source:** FoxIO JA4+ ([v1.0.1 release](https://github.com/FoxIO-LLC/ja4/releases/tag/v1.0.1), [Rust TCP implementation](https://github.com/FoxIO-LLC/ja4/blob/v1.0.1/rust/ja4/src/tcp.rs)); vendor/community construction, not an IETF standard. **Source tag commit:** `896b951e438c2979e0ef077a94ad390b1c973c23`. **Checked:** 5 November 2026.

| Aspect | Definition / decision |
|---|---|
| Message and direction | Client TCP initial SYN (SYN set, ACK clear), before TLS. The cited implementation uses the first eligible SYN. |
| Input components | Advertised TCP receive window, TCP option-kind sequence, MSS, and window scale. |
| Canonicalization | Human-readable structured value; TCP option order is preserved. It is not JA4's sorted TLS extension hash. Pin the implementation because formatting and collection choices are tool-specific. |
| Visibility | TCP header fields are visible without TLS secrets, subject to capture vantage, truncation, offload, and path effects. |
| Protocol references | TCP header/options: [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html); MSS: [RFC 6691](https://www.rfc-editor.org/rfc/rfc6691.html). These define TCP behavior, not JA4T. |
| Interpretation limit | It describes the TCP endpoint visible at the observation point. NAT alone does not prove TCP termination; a proxy may create separate legs. A single MSS, TTL, or JA4T value does not prove proxying, identify the remote application, or establish OS misclassification. |
| Project status | L3 is a secondary investigation. Current paired traces show different TCP legs/profiles but do not establish a termination mechanism or JA4T attribution error. |
