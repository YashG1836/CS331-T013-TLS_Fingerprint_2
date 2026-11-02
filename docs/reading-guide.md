# Team reading guide: TLS, fingerprints, visibility, and QUIC

This is a shared primer for the Project 2 team. It explains the concepts behind the named RFCs and tells you what to extract from each reading. It is not a substitute for the RFC text: use the RFC sections for normative details, and cite those sections in the report. Do not copy a claim from this guide into the findings ledger without checking the specification and the relevant capture.

## Suggested order

1. Read **Part I** before changing the QUIC parser.
2. Read **Part II** before using or discussing JA3/JA4, TCP/IP fingerprints, or passive visibility.
3. Read **Part III** as the corresponding experiments begin; these are not prerequisites for the first QUIC v1 Initial path.
4. Complete the short exercises at the end and discuss the answers as a team.

The links below point to the RFC Editor's published RFCs. For a newer protocol or draft that is not an RFC, record the version and access date in the experiment metadata.

---

# Part I — the QUIC extractor foundations

## 1. TLS handshake messages, TLS records, and QUIC CRYPTO frames

TLS has more than one layer of framing. A TLS **handshake message** begins with a one-byte message type and a three-byte body length. A ClientHello is one such message. On a TCP connection, TLS handshake bytes are carried inside TLS records, which in turn are carried by TCP. A TCP read, TCP segment, TLS record, and TLS handshake message are not guaranteed to have matching boundaries.

QUIC uses TLS 1.3 for the handshake, but QUIC does **not** carry the handshake in TLS records. Instead, the TLS implementation supplies handshake bytes to QUIC; QUIC carries them in **CRYPTO frames**. A CRYPTO frame includes an offset, so the bytes form a reassembled handshake stream for an encryption level. The QUIC layer handles packet protection and transport; the TLS layer handles the handshake and its cryptographic negotiation.

For this project, the client ClientHello is in client Initial CRYPTO data. The extractor therefore has to:

1. Identify a QUIC Initial packet and its bounds.
2. Decrypt the packet payload.
3. Parse its frames and find CRYPTO frames.
4. Place each CRYPTO fragment at its offset, rather than append in packet-arrival order.
5. Wait until the handshake header and its declared message length are present.
6. Parse the completed ClientHello.

CRYPTO data is associated with a connection direction and encryption level. Do not combine unrelated connections, directions, or encryption levels in one reassembly buffer. A ClientHello split over multiple packets is one handshake message; the packet boundaries do not define TLS-message boundaries.

**Read:** [RFC 8446 §4.1.2](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.1.2) for ClientHello; [RFC 9001 §4.1](https://www.rfc-editor.org/rfc/rfc9001.html#section-4.1) for the TLS handshake over QUIC; [RFC 9000 §19.6](https://www.rfc-editor.org/rfc/rfc9000.html#section-19.6) for CRYPTO frames.

**Check your understanding:** Why is searching the UDP payload for the byte pattern of a ClientHello not a valid extractor? What information lets you put a CRYPTO fragment at the right place?

## 2. QUIC packet structure and datagram boundaries

QUIC runs over UDP, but a UDP datagram is not necessarily one QUIC packet. A datagram can contain coalesced QUIC packets. Long-header packets include a version, destination and source connection IDs, and type-specific fields. For Initial packets, there is also a token-length/token field. The packet-length field identifies the protected packet boundary, including the packet number and protected payload. Correctly respecting that boundary is necessary before attempting packet protection.

QUIC variable-length integers use the first two bits to signal the encoded width. They are not ordinary fixed-width network integers. Parse them with a bounds-checked decoder and reject truncated encodings.

The packet number is protected on the wire and is encoded in a truncated form. After removing header protection, reconstruct the full packet number using the expected packet number and the number of encoded bits. A decoder that always treats the truncated value as the full packet number will eventually fail.

**Read:** [RFC 9000 §12.2](https://www.rfc-editor.org/rfc/rfc9000.html#section-12.2) for packet coalescing; [§16](https://www.rfc-editor.org/rfc/rfc9000.html#section-16) for variable-length integers; [§17.1](https://www.rfc-editor.org/rfc/rfc9000.html#section-17.1) for packet numbers; [§17.2](https://www.rfc-editor.org/rfc/rfc9000.html#section-17.2) and especially [§17.2.2](https://www.rfc-editor.org/rfc/rfc9000.html#section-17.2.2) for long-header and Initial packet formats.

For the currently supported QUIC v1 path, do not implement Retry, 0-RTT, migration, short headers, or other versions by inference. Read their specific sections before adding support.

## 3. Initial keys, HKDF, AEAD, and header protection

### HKDF in two steps

HKDF has two conceptual operations:

- **Extract:** takes input keying material and a salt and produces a pseudorandom key (PRK).
- **Expand:** uses the PRK and context information to produce keying material of a requested length.

TLS 1.3 defines a labelled expansion format, `HKDF-Expand-Label`, which encodes the output length, a label, and a context. QUIC uses this TLS construction to derive packet-protection material.

For QUIC v1 Initial protection, the destination connection ID and the fixed Initial salt feed the initial secret derivation. The resulting secret is split into client and server Initial secrets; each side's secret is expanded into a packet key, IV, and header-protection key. The exact bytes, labels, and lengths are protocol-defined—do not substitute a remembered salt or invent labels.

Initial keys are deliberately derivable by an observer: the salt is public and the Initial destination connection ID is visible in the packet. Initial encryption therefore does not provide confidentiality against a passive observer. It does provide packet protection/integrity as specified by QUIC. Do not generalize that observation to later QUIC encryption levels.

### AEAD packet protection

An AEAD algorithm encrypts plaintext and authenticates it together with associated data. For QUIC packet protection, the unprotected packet header through the packet number is associated data; the payload is encrypted and authenticated. A failed authentication check means the packet must be rejected. Never return candidate plaintext after a tag failure.

The nonce is derived from the packet IV and packet number according to the RFC. The exact construction matters: a wrong packet number or nonce causes authentication failure.

### Header protection

QUIC header protection is separate from AEAD payload protection. It masks selected bits of the first header byte and the packet-number bytes using a sample from the protected packet. The receiver must obtain the sample, remove the mask, recover the packet-number length and value, and then use the unprotected header as AEAD associated data. Do not attempt payload AEAD decryption first.

**Read:** [RFC 5869 §§2.1–2.2](https://www.rfc-editor.org/rfc/rfc5869.html#section-2.1) for HKDF-Extract and HKDF-Expand; [RFC 8446 §7.1](https://www.rfc-editor.org/rfc/rfc8446.html#section-7.1) for TLS 1.3 secret derivation and labelled expansion; [RFC 9001 §5.2](https://www.rfc-editor.org/rfc/rfc9001.html#section-5.2) for Initial secrets and [§§5.3–5.4](https://www.rfc-editor.org/rfc/rfc9001.html#section-5.3) for packet protection and header protection. For the generic AEAD interface, see [RFC 5116 §2](https://www.rfc-editor.org/rfc/rfc5116.html#section-2).

### OpenSSL concepts to learn

Use OpenSSL's maintained APIs rather than writing AES, HMAC, or HKDF. Learn the EVP abstraction used for ciphers and authenticated decryption, and OpenSSL 3's KDF interface. In particular, understand how to set the digest, salt, input key, info/label, and output size; how GCM associated data and the authentication tag are passed; and how an authentication failure is reported. Check the OpenSSL version on the test machine and consult documentation for that version.

The API is not the specification. First derive the exact inputs and outputs from RFC 9001; then map those values onto OpenSSL calls. A successful API call is not evidence that the inputs were assembled correctly, so test against published vectors.

## 4. CRYPTO reassembly and safe parsing

Treat CRYPTO frames as offset-labelled byte ranges. A robust reassembler should:

- Accept a fragment that arrives before an earlier-offset fragment.
- Recognize an identical retransmitted/overlapping byte as duplicate data.
- Reject overlapping bytes that conflict.
- Report gaps and incomplete data distinctly from malformed input.
- Bound the maximum offset and amount of memory retained.
- Avoid integer overflow when calculating `offset + length`.
- Emit a handshake only after the full declared handshake length is available.

The TLS handshake header is four bytes: message type plus a three-byte body length. Validate that the message type is ClientHello and that the length is complete before parsing the body. Then validate nested vector lengths before reading cipher suites, compression methods, or extensions. Length fields are untrusted packet input, not allocation instructions to follow blindly.

In C++20, use bounded views such as `std::span<const std::uint8_t>`, fixed-width integer types, and explicit checks before each read. Prefer returning a clear parse error over reading beyond the input or silently returning partial fields.

---

# Part II — fingerprint construction and passive visibility

## 5. JA3 and JA4: what a fingerprint means

A TLS fingerprint summarizes selected observable properties of a handshake. It can be useful evidence about a TLS library, version, configuration, or application. It is **not** proof of a unique application, user, or identity. Different applications may share a TLS stack; one application may change its handshake across versions, configuration, or connections.

JA3 constructs a canonical text representation from selected ClientHello values (including the offered version, cipher suites, extension types, supported groups, and EC point formats), applies GREASE handling, and hashes the result with MD5. JA3S applies a related construction to selected ServerHello fields. MD5 here is a compact identifier, not a security guarantee.

JA4 uses a different, multi-part representation. Its construction normalizes selected values and includes a readable prefix plus hashed components. Sorting and exclusion rules are part of the fingerprint specification, not details that can be guessed from the output. JA4's protocol marker and QUIC handling must be confirmed against the current FoxIO JA4+ specification and a reference implementation before code emits a QUIC JA4 value. Compare parsed fields as well as the final string; a coincidentally matching hash does not validate the parser.

JA4T uses TCP handshake observations; JA4X uses certificate characteristics; JA4H uses HTTP characteristics. These signals observe different layers and have different capture and decryption requirements. Do not compare their outputs as if they were all computed from the same packet fields.

**Read:** [Salesforce's JA3 repository](https://github.com/salesforce/ja3) for the JA3 description and reference implementation; [FoxIO's JA4 repository](https://github.com/FoxIO-LLC/ja4) for the maintained JA4/JA4+ specification; and the [tshark manual](https://www.wireshark.org/docs/man-pages/tshark.html) plus Wireshark's TLS dissector documentation for the version used in experiments. Record exact versions and commands. Treat ja4db as a provenance-bearing hint, not ground truth.

## 6. GREASE

GREASE reserves values that clients can send to make protocol implementations tolerate unknown values. A parser must distinguish a GREASE value from an ordinary value and follow the fingerprint's own exclusion rules. Do not strip values merely because they look unusual, and do not assume every tool applies the same rule to every vector.

**Read:** [RFC 8701](https://www.rfc-editor.org/rfc/rfc8701.html), especially its definition and use of GREASE values. Then verify the particular JA3/JA4 normalization rules from those fingerprint specifications. RFC behaviour and fingerprint canonicalization are related but not interchangeable.

## 7. TCP fingerprints and vantage point

TCP fingerprinting observes properties of the TCP connection setup, usually the SYN and its options. RFC 9293 defines TCP and its options; a fingerprint construction chooses a subset and an ordering/encoding. The SYN is essential evidence. If a capture begins after the handshake, it cannot establish the original SYN properties. A proxy or relay may create a new TCP connection, so the observed TCP stack may be the intermediary's rather than the client application's.

Capture offloads, NAT, relays, and capture location can affect what is visible. Record the interface, direction, capture point, proxy/NAT conditions, and offload settings. A difference caused by the observation path must not be described as a change in the TLS client.

**Read:** [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html) for TCP; for any IP/TCP fields used by the particular JA4T construction, cite the relevant protocol section and the fingerprint specification separately.

## 8. IPv6: separate the TLS signal from the network signal

IPv6 and its extension headers affect the network-layer packet layout and path behaviour. IPv6 privacy addresses can also change over time. Those facts can matter to flow correlation, transport fingerprints, and capture parsing. They do not automatically change a TLS-only ClientHello fingerprint: if the same ClientHello bytes are sent over IPv4 and IPv6, a fingerprint based only on those bytes should remain the same.

Keep the hypotheses separate: (a) did the TLS fields change? (b) did the transport/network fields change? (c) did attribution or flow tracking become harder? Report which layer each measurement belongs to.

**Read:** [RFC 8200](https://www.rfc-editor.org/rfc/rfc8200.html) for IPv6; [RFC 8201](https://www.rfc-editor.org/rfc/rfc8201.html) for IPv6 Path MTU Discovery; [RFC 8981](https://www.rfc-editor.org/rfc/rfc8981.html) for temporary address extensions. Use the sections that correspond to the exact field or behaviour you report.

## 9. Certificate compression versus certificate abridging

RFC 8879 defines TLS certificate compression. Compression changes how a certificate message is represented; it is not the same claim as replacing a certificate with a hash or Merkle proof. If the observer has the necessary plaintext and supports the negotiated compression algorithm, compressed certificate data may be processed according to the RFC. Without TLS secrets, TLS 1.3 encrypts the certificate handshake message from a passive tap.

Keep future certificate-abridging proposals separate from RFC 8879 and from captured results. Unless a deployed implementation is captured, label an abridging discussion as analysis or simulation—not an observed limitation.

**Read:** [RFC 8879](https://www.rfc-editor.org/rfc/rfc8879.html), then the relevant current draft/specification for any particular abridging design. Record its publication status and date.

## 10. Encrypted DNS and hostname attribution

DoH and DoQ protect DNS queries using HTTPS and QUIC respectively. Encrypting DNS does not, by itself, rewrite the TLS ClientHello of a separate connection. It can remove a passive observer's ability to correlate a DNS lookup with a later connection using the plaintext DNS name. This is an attribution-context change, not automatically a fingerprint change.

**Read:** [RFC 8484](https://www.rfc-editor.org/rfc/rfc8484.html) for DNS over HTTPS and [RFC 9250](https://www.rfc-editor.org/rfc/rfc9250.html) for DNS over QUIC. In the experiment, separate the DNS flow from the TLS/QUIC flow and state exactly what the observer can see at each vantage point.

## 11. ECH and the visible ClientHello

Encrypted ClientHello (ECH) protects the sensitive inner ClientHello using HPKE, while an outer ClientHello remains available for the TLS connection setup. A passive observer may therefore see outer-handshake properties while not seeing the inner server name and other protected values. Do not describe ECH as making every ClientHello field disappear: determine which fields are in the outer versus inner hello and what the capture and selected tool actually expose.

HPKE is a cryptographic construction used by ECH; reading its RFC gives the cryptographic background, but the ECH RFC specifies how it is used in TLS. Do not implement ECH as part of the QUIC Initial extractor unless that becomes an explicit scope item.

**Read:** [RFC 9849](https://www.rfc-editor.org/rfc/rfc9849.html) for TLS Encrypted ClientHello and [RFC 9180](https://www.rfc-editor.org/rfc/rfc9180.html) for HPKE. Project documents referring to the earlier `tls-esni` draft should be updated to cite the finalized specification where applicable.

## 12. HTTP fingerprints and encryption

HTTP fingerprints operate above TLS. HTTP/2 compresses header fields with HPACK; HTTP/3 uses QPACK. A passive observer without TLS traffic secrets cannot normally inspect TLS 1.3 application data, so it cannot simply read the HTTP headers from encrypted traffic. With keys, analysis must still account for the relevant HTTP version and header compression. This is why JA4H's visibility conditions differ from a ClientHello-based fingerprint.

**Read:** [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html) for HTTP/2 and its header compression; [RFC 9204](https://www.rfc-editor.org/rfc/rfc9204.html) for QPACK. Read the TLS key-log documentation for each reference tool used, and record whether secrets were supplied during analysis.

---

# Part III — optional extension: QUIC v2

QUIC v2 is a different QUIC version, not permission to reuse the v1 constants. Version-dependent packet type interpretation and Initial key derivation must follow the v2 specification. Detect and dispatch on the version first; keep v1 and v2 test vectors separate. Implement v2 only after the v1 parser, decryption, and reassembly pass their acceptance tests.

**Read:** [RFC 9369](https://www.rfc-editor.org/rfc/rfc9369.html), alongside the corresponding QUIC v1 sections in RFC 9000 and RFC 9001. Make a table of each version-dependent value or rule before changing code.

---

# Team exercises before claiming a result

1. Draw the byte path from a UDP datagram to a parsed ClientHello. Label every layer and every length/offset field.
2. Explain why QUIC Initial decryption is possible to a passive observer, and why that does not mean later handshake or application packets are also decryptable.
3. Given two CRYPTO fragments arriving in reverse order, show where their bytes go. Then show what the reassembler should do for an identical overlap, a conflicting overlap, and a gap.
4. Pick one JA3 or JA4 field. State its input bytes, normalization rule, fingerprint-specification source, and relevant RFC section. Explain which endpoint controls it.
5. For each of JA4, JA4T, JA4X, and JA4H, state the needed packet/layer, capture condition, and whether TLS secrets may be required.
6. Explain why DoH can reduce hostname correlation without necessarily changing the ClientHello fingerprint.
7. Explain the difference between certificate compression and certificate abridging, and what evidence would be needed to claim either was observed.
8. Explain why the same TLS fingerprint is not proof of one unique application or user.

A claim is ready for the report only when the team can explain the protocol mechanism, cite the exact specification section, and reproduce the measured value from committed evidence.
