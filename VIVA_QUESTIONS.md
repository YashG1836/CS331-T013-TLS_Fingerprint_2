# Viva questions with short answers

This is an adopted study guide. Track 1 numbers below are team-supplied and provisional; consult `docs/track1-evidence-audit.md` before presenting them as results. Learn the answers in your own words; do not read them out. “Tn” points to the corresponding test explanation, not a claim that the experiment has been independently rerun in this checkout.

## A. Basics

1. **Why fingerprint at all?**
   The application data is encrypted, but visibility depends on the protocol: an ordinary TLS-over-TCP ClientHello is normally visible unless ECH is used; a QUIC v1 ClientHello is carried in protected Initial packets whose keys are derivable from public inputs. A passive observer can recover those Initial bytes, then examine the client-offered ciphers, extensions, and ordering. This identifies a software configuration imperfectly; it does not identify a person or guarantee a unique application.

2. **How visible is the ClientHello?**
   For TLS over TCP it is normally visible unless ECH is used. In QUIC v1 the Initial packet is protected, but its Initial keys are derivable from public inputs, so a passive observer can recover the outer ClientHello. The QUIC Handshake packets use different, non-public secrets.

3. **The data is unencrypted anyway, so why "fingerprint" it?**
   Each field alone means little. The combination and the order is what differs between libraries. Sir's analogy: same words, different way of speaking.

4. **ServerHello: isn't it always the same?**
   No. The server picks from what the client offered, so JA4S depends on the server **and** the client. Our data: the same Cloudflare server gave JA4S `..._1302_...` to curl and both `..._1301_...` and `..._1302_...` to Chromium (our data: T5, `results/summary.json`, field `ja4s_foxio`).

5. **TLS 1.2 vs 1.3?**
   - In TLS 1.3 everything after ServerHello is encrypted, including the certificate (RFC 8446 §2).
   - The real version sits in the `supported_versions` extension; the old version field stays 0x0303.
   - TLS 1.3 removed RSA key exchange, compression and renegotiation (RFC 8446 §1.2), and has 5 cipher suites (RFC 8446 Appendix B.4).
   - Effect for us: certificate fingerprints (JA4X) need the keys on TLS 1.3 (our data: T2).

6. **Where do the fields come from?**
   | Field | RFC |
   |---|---|
   | ciphers, extensions, versions | RFC 8446 §4.1.2 |
   | SNI | RFC 6066 §3 |
   | ALPN | RFC 7301 |
   | GREASE | RFC 8701 |
   | TCP options (JA4T) | RFC 9293 §3.1 |
   | QUIC Initial | RFC 9000 §17.2, RFC 9001 §5 |

7. **Why these fields and not others?**
   They are set by the software and stay the same between connections. Random fields (client random, session id, key share bytes) change every time, so they're left out.

8. **Hash length, and why hash?**
   - JA3 = MD5 of the field list, 32 hex characters.
   - JA4 = `a_b_c`, 36 characters. `a` is readable (protocol, version, SNI yes/no, number of ciphers, number of extensions, ALPN). `b` = first 12 hex of SHA-256 of the sorted ciphers. `c` = first 12 hex of SHA-256 of the sorted extensions + signature algorithms.
   - The hash is only a short key for lookup and sharing. It is not for security.

9. **Why not include the destination IP?**
   The fingerprint should describe the client software. The IP belongs to the server, and many websites can sit behind one IP (that's why SNI exists).

10. **Does it identify a user or an app?**
    It identifies a TLS library + its settings. curl and Python use the same OpenSSL and share JA4 part b, but differ in parts a and c (our data: T5). One app can also have many JA4s (our data: T5, Chromium).

11. **What is SNI?**
    The server name in the outer ClientHello (RFC 6066 §3), normally visible unless ECH is used. In QUIC v1, the outer ClientHello is recoverable from Initial packets. JA4 records whether SNI is present, not the site name itself.

12. **eSNI / ECH?**
    eSNI was an older draft that encrypted only the SNI. It was replaced by ECH, which encrypts the whole real ClientHello with a key the server publishes in DNS (HTTPS record, RFC 9460). Outside, only a shared name is visible. Our data: the outer name was `cloudflare-ech.com`, and Cloudflare's page said `sni=encrypted` (T7).

13. **What is GREASE?**
    Random reserved values (0x0a0a, 0x1a1a, … 0xfafa, 16 of them, RFC 8701) that clients add so servers don't break on unknown values. Fingerprints must ignore them.

14. **What did the Chromium-repeat sample show about JA3 and JA4?**
    The imported T5 summary reports 50 distinct JA3s and 15 released-tool JA4s across 50 Chromium ClientHellos; a specified unreleased FoxIO commit reports one JA4. The team's GREASE explanation is plausible but needs verification against the pinned source and raw values before asserting causation. These are tool-output observations, not results from our C++ parser.

## B. Our method

15. **Why Python and not C/Rust? (asked in Phase 1)**
    This time we don't compute fingerprints at all. Wireshark/tshark (written in C) and FoxIO ja4 (written in Rust) do. Python only starts the tools and counts the results.

16. **Why not write your own?**
    Sir asked us to use the existing tools and find where they fail, because those tools are what people actually run.

17. **How do you validate the output?**
    - The imported analysis compared TShark and FoxIO on the same PCAP; nonempty rows report matching JA4 values. The empty IPv6 PCAP is not a comparison and is marked not comparable in our audited summary.
    - FoxIO's Rust CLI uses TShark for packet dissection, so agreement is not between independent packet parsers.
    - Reproduction with pinned binaries and a byte-level comparison are still required; see `docs/track1-evidence-audit.md`.

18. **Performance? (asked in Phase 1)**
    On our small pcaps, tshark takes about 0.06 s and ja4 about 0.12 s per file (`seconds_*` columns in `results/summary.md`). We did not test big captures, so we don't claim anything more.

19. **How are AI use and decisions documented?**
    A generated summary does not substitute for the course's AI-use record or the team's decisions. Those records must be maintained authentically by the team; the imported Track 1 archive's prompt history was not added to this repository.

20. **Who keeps the fingerprint database up to date?**
    FoxIO keeps a mapping file (`ja4plus-mapping.csv` in their repo) and the ja4db.com site. Our T5 result shows why a database alone is risky: one browser gave 15 JA4s with the released tools.

## C. Limitations (our tests)

21. **QUIC: how can a passive observer recover an Initial?**
    QUIC v1 Initial secrets are derived from a public salt and the packet's DCID (RFC 9001 §5.2). Initial protection therefore does not hide the ClientHello from an observer who implements the derivation. Later Handshake packets use secrets that are not public. The imported T1 reference outputs report five ClientHellos per client. Our current C++ PCAP CLI also recovers five from each. The user reports all ten are byte-identical to TShark 4.6.4 `tls.handshake_raw` values by set comparison on Ubuntu WSL. The raw exports and comparison script are not yet retained in the repo, so attribute the result to that reported run rather than claiming independent reproduction.

22. **Why remove header protection before decrypting?**
    The packet number is hidden by header protection, and the packet number is needed to build the decryption nonce (RFC 9001 §5.3, §5.4).

23. **Why join CRYPTO frames by offset?**
    The ClientHello can be split into many CRYPTO frames; arrival order isn't byte order (RFC 9000 §19.6). Our data: Chromium's QUIC hello came in 21 fragments (T1).

24. **Post-quantum key share: what changes in the imported sample?**
    T4's summary reports a 508-to-1511-byte ClientHello difference and selected groups 29 vs 4588. JA4 differs alongside extension-set differences; it should not be described as directly encoding the selected group. Segment counts depend on the capture/offload setting; see the T3 discrepancy note.

25. **IPv6?**
    Not measured: our network has no IPv6 (T6). What we'd check: same JA4 expected (JA4 has no IP field); TCP MSS and IP-based attribution could change.

26. **Encrypted DNS?**
    DoH hides DNS requests from passive observers on the network path; it does not itself change the ClientHello. T7's saved page outputs report the site SNI as encrypted with ECH on. The intended ECH+DoH page did not load in the imported run, so that arm remains incomplete.

27. **GRO/GSO/TSO (capture settings)?**
    These affect segmentation/aggregation at the host. The imported summary reports `pieces_max` 1 vs 2 with offload on/off, but its frame-size aggregates do not match the T3 narrative's 1586/1514+138 values. The Docker capture is not a wire-side measurement; the comparison needs a targeted rerun.

28. **Certificate compression / abridged certificates?**
    RFC 8879 compresses certificates; newer drafts replace them with shorter references. Then JA4X has less or nothing to read. We couldn't capture this; we only mention it.

29. **JA4X / JA4H without keys?**
    The imported T2 summary reports zero without a key log and five with one. The key log is intentionally absent, so the keyed result cannot be regenerated from the committed repository.

## D. Big picture

30. **Why isn't fingerprinting thrown away?**
    It can be a low-cost signal, but does not identify a person and depends on client versions, settings, and vantage. The imported Track 1 set includes incomplete cases (notably zero-packet IPv6 and failed DoH), so avoid saying every test succeeded.

31. **What candidate limitations did the imported sample raise?**
    - release-specific Chromium JA4 instability (T5, pending root-cause verification)
    - ClientHello/JA4 variation across the tested curve settings (T4)
    - JA4X/JA4H visibility with versus without keys (T2, keyed data not reproducible without the uncommitted key log)
    - capture-vantage sensitivity (T3, metrics need reconciliation)
    - ECH outer-name behavior (T7; the DoH arm is incomplete)

    These are scoped observations, not universal claims.

32. **Alternatives?** (background reading, not tested by us)
    - other parts of the JA4+ family: JA4T (TCP), JA4H (HTTP), JA4X (certificate), JA4L (latency)
    - HTTP/2 fingerprinting
    - active probing of servers (JARM)
    - machine learning on packet sizes and timing

33. **What would make the technique useless?**
    If every client sent the same ClientHello (same library, same settings), it would carry no information.

34. **Can every number be regenerated from this checkout today?**
    Not yet. `make lab-eval` is the reproduction path when Docker is available and writes to `results/reproduced/`; committed outputs are imported and remain separately identified. The key-log arm needs a local key log, the IPv6 arm needs a working IPv6 network, and the T3 narrative needs targeted raw queries.
