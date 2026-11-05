# Glossary: every term used in this repo, in simple words

Read top to bottom the first time; each section builds on the one before.

## 1. Standards
| Term | Meaning |
|---|---|
| **IETF** | Internet Engineering Task Force: the group that writes the rules for internet protocols. |
| **RFC** | "Request for Comments": an official IETF document that defines a protocol. Example: RFC 8446 = TLS 1.3. "RFC 8446 §4.1.2" means section 4.1.2 of that document. |
| **Draft** | An IETF document that isn't an RFC yet and can still change (e.g. the ECH draft). |
| **IANA** | Keeps the official lists of numbers used in protocols (e.g. which number means which cipher or group). |

## 2. Networks basics
| Term | Meaning |
|---|---|
| **Packet** | One small piece of data sent over the network. Big messages are split into many packets. |
| **Frame** | A packet as seen on the cable/link, including the Ethernet header. tcpdump records frames. |
| **IP / IPv4 / IPv6** | The addressing layer. IPv4 addresses look like `104.16.124.96`; IPv6 is the newer, longer format. |
| **Privacy addresses** | IPv6 addresses that change over time so a device can't be tracked by IP (RFC 8981). |
| **TCP** | Reliable connection on top of IP. Used by normal HTTPS. Starts with SYN → SYN-ACK → ACK. |
| **SYN / SYN-ACK** | The first two packets of a TCP connection (client asks, server answers). They carry TCP options. |
| **UDP** | Simple, connectionless transport. QUIC runs on top of UDP. |
| **Port** | A number that says which service a packet is for. HTTPS = 443, DNS = 53. |
| **MTU** | Maximum Transmission Unit: the biggest packet a link allows. Normal internet = 1500 bytes. |
| **MSS** | Maximum Segment Size: the biggest TCP payload a side wants to receive. Sent in the SYN. Usually MTU − 40 (1460). |
| **TTL** | Time To Live: a counter in every IP packet, reduced by 1 at each router. |
| **Segment** | One TCP packet's worth of data. A big ClientHello can need 2 segments. |
| **TSO / GSO / GRO** | Kernel/network-card tricks: hand over one big packet and cut it up later (TSO/GSO, sending), or join many packets into one (GRO, receiving). They make captures show packets that never existed on the wire. |
| **NAT** | Network Address Translation: a box that rewrites addresses, e.g. your home router. |
| **Proxy** | A machine in the middle that ends your connection and opens a new one for you. |
| **Vantage point / tap** | *Where* the capture is taken. A "tap" is a passive capture point that only listens. |
| **DNS** | Turns a name (`crypto.cloudflare.com`) into an IP address. Normally plaintext on port 53. |
| **DoH** | DNS over HTTPS: DNS sent inside encrypted HTTPS, so others can't see the lookup (RFC 8484). |
| **HTTPS record** | A newer DNS record type (RFC 9460). Among other things it carries the server's ECH key. |

## 3. TLS (the encryption in HTTPS)
| Term | Meaning |
|---|---|
| **TLS** | Transport Layer Security: encrypts web traffic. TLS 1.3 = RFC 8446. (SSL is its old name.) |
| **Handshake** | The first messages, where client and server agree on how to encrypt. |
| **ClientHello** | The first TLS handshake message, from the client. In ordinary TLS over TCP it is visible unless ECH hides the inner hello. In QUIC v1 it is carried in protected Initial packets, but a passive observer can derive the Initial keys and recover it. **This is what we fingerprint.** |
| **ServerHello** | The server's answer: picks one cipher and key share. It is plaintext in the TLS-over-TCP handshake, but QUIC carries it in protected Handshake packets (whose keys are not public Initial keys). |
| **Cipher suite** | A named set of encryption algorithms (e.g. `0x1302` = AES-256-GCM with SHA-384). |
| **Extension** | An optional extra field in the hello, each with a number (e.g. `0x0000` = SNI, `0x0010` = ALPN). |
| **SNI** | Server Name Indication: the website name in the ClientHello. Normally visible in the outer hello; with ECH the real name is in the encrypted inner hello. QUIC Initial packet protection can be removed by a passive observer. |
| **ALPN** | Says which app protocol will be used inside TLS: `h2` = HTTP/2, `http/1.1`, `h3` = HTTP/3. |
| **Signature algorithms** | Extension listing which signature types the client accepts (RFC 8446 §4.2.3). |
| **Supported groups** | Extension listing which key-exchange methods the client supports. |
| **Key share / key exchange** | The client's public key material for agreeing on a secret key (RFC 8446 §4.2.8). |
| **X25519** | A common classic key-exchange group. Number 29. |
| **Post-quantum (PQ)** | Crypto designed to stay safe even against future quantum computers. |
| **ML-KEM** | A post-quantum key-exchange method (standardised by NIST). Its keys are large (~1.2 KB). |
| **X25519MLKEM768** | A "hybrid" group = X25519 + ML-KEM together. Number 4588 (hex 0x11EC). |
| **GREASE** | Random fake values (0x0a0a, 0x1a1a … 0xfafa, 16 total) that clients insert so servers learn to ignore unknown values (RFC 8701). Fingerprints must skip them. |
| **Padding extension** | Filler bytes added to a hello to change its size (RFC 7685). OpenSSL adds it to hellos of 256–511 bytes, when the app turns that option on, to avoid a bug in old F5 load balancers. curl's small hello in T4 had it. |
| **ec_point_formats** | An old extension about elliptic-curve formats (RFC 8422). |
| **Certificate / X.509** | The server's ID card, signed by a trusted authority. In TLS 1.3 it is sent encrypted. |
| **Certificate compression / abridged certificates** | Ways to send a smaller certificate (RFC 8879) or only a reference to it (newer drafts). |
| **Key log / SSLKEYLOGFILE** | If you set this variable, curl/Chrome write their session keys to a file, so Wireshark can decrypt *that* session. Real networks never have it. |
| **AEAD** | The kind of encryption TLS 1.3 and QUIC use: encrypts and checks for tampering at once (e.g. AES-GCM). |
| **ECH** | Encrypted ClientHello: the real ClientHello (with the real SNI) is encrypted inside an outer one that shows only a shared name. |
| **eSNI** | Older draft that encrypted only the SNI; replaced by ECH. |
| **public_name** | The shared name shown in the outer ClientHello when ECH is used (we saw `cloudflare-ech.com`). |

## 4. QUIC
| Term | Meaning |
|---|---|
| **QUIC** | A newer transport over UDP with TLS 1.3 built in (RFC 9000, RFC 9001). Used by HTTP/3. |
| **HTTP/3** | HTTP over QUIC. |
| **Initial packet** | The first QUIC packets. They carry the ClientHello. They're encrypted, but with keys anyone can compute. |
| **Connection ID** | A number in each QUIC packet that identifies the connection. The Initial keys are made from it. |
| **Salt** | A fixed public value mixed into key making. QUIC v1's Initial salt is printed in RFC 9001 §5.2. |
| **Header protection** | An extra mask that hides the packet number in QUIC packets (RFC 9001 §5.4). |
| **CRYPTO frame** | A piece of the TLS handshake inside a QUIC packet. A ClientHello can be split into many (we saw 21). |
| **Connection migration** | A QUIC connection moving to a new network path (e.g. Wi-Fi → mobile data) without a new handshake (RFC 9000 §9). |
| **Retry / 0-RTT / QUIC v2** | Other QUIC features/versions we haven't tested. |

## 5. Fingerprints
| Term | Meaning |
|---|---|
| **Fingerprint** | A short string made from how a client fills its hello. It identifies the software (library + settings), not the person. |
| **Hash** | A function that turns any input into a short fixed-length string. Same input → same output. |
| **MD5 / SHA-256** | Two hash functions. JA3 uses MD5 (32 hex chars). JA4 uses SHA-256, cut to 12 hex chars. |
| **JA3** | Older fingerprint (by Salesforce): MD5 of version, ciphers, extensions, groups, point formats, **in the order sent**. |
| **JA3S** | JA3 for the ServerHello. |
| **JA4** | Newer fingerprint (by FoxIO): `a_b_c`. a = readable summary, b = hash of *sorted* ciphers, c = hash of *sorted* extensions + signature algorithms. |
| **ja4_r** | The "raw" JA4: the same parts before hashing, so you can see the actual values. |
| **JA4S** | JA4 for the ServerHello. |
| **JA4X** | Fingerprint of the server's certificate. |
| **JA4H** | Fingerprint of the HTTP request (headers, cookies). |
| **JA4T / JA4TS** | Fingerprint of the TCP SYN / SYN-ACK (window size, options, MSS). |
| **JA4L** | Latency measurement between client and server. |
| **JA4+** | The whole FoxIO family above. |
| **Collision** | Two different apps giving the same fingerprint. |
| **Stable** | The same app always gives the same fingerprint. |

## 6. Tools
| Term | Meaning |
|---|---|
| **pcap** | A file of captured packets. Our evidence lives in `captures/pcaps/*.pcap`. |
| **tcpdump** | Command-line program that captures packets into a pcap. |
| **Wireshark / tshark** | The most used packet analyser (written in C). tshark is its command-line version. It also computes JA3/JA4. |
| **FoxIO ja4** | FoxIO's official JA4+ command-line tool (written in Rust). Reads packets through tshark. |
| **ja4-main** | Our build of FoxIO's newest *unreleased* code, used only to compare with the release. |
| **Release / tag / commit** | A commit is one saved change in git; a tag names a commit as a release (e.g. `v0.18.6`). "Unreleased" = in the code but not in any release yet. |
| **Upstream** | The original project (FoxIO, Wireshark), as opposed to our copy. |
| **Chromium** | The open-source browser that Chrome is built from. We used version 156. |
| **curl** | Command-line program that downloads URLs. Uses OpenSSL here. |
| **OpenSSL** | The TLS library used by curl and Python on Linux. |
| **Docker / container / image** | Docker runs a small Linux system (a *container*) from a recipe (the *image*, built from `code/Dockerfile`). We use it as our Linux VM. |
| **Makefile / make** | Short named commands (`make lab-eval`) that run longer ones. |
| **Manifest** | Our list of all tests: `captures/manifest.json`. |
| **JSON** | A simple text format for data (`{"key": "value"}`). |
| **pytest** | Python test runner. Runs the repository's manifest, baseline, preflight, and Track 1 script tests. |
| **CMake / CTest** | Build and test tools for the teammates' C++ code. |
| **Sanitizers (ASan/UBSan)** | Compiler options that crash the program loudly on memory bugs. Used to check the C++ code. |

## 7. Words about our method
| Term | Meaning |
|---|---|
| **Hypothesis** | What we *expect* before testing. Can turn out wrong (T1 did). |
| **Control** | The normal case we compare against, so a difference means something. |
| **Variable** | The one thing we change in a test. |
| **Regenerate** | Rerun `make lab-eval` in the recorded lab image to produce fresh outputs under `results/reproduced/`; compare them with the imported summary and explain any version-dependent differences. |
| **Limitation (L1–L8)** | A situation where real fingerprinting tools don't give a useful/correct answer. |
| **Track 1 / Track 2** | Track 1 = reference tools, captures, and evidence (15 attempts imported; some rows remain incomplete). Track 2 = the modular QUIC C++ core and its real-capture integration (next). |
