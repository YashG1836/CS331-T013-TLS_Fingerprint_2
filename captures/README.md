# Capture corpus

- `captures/manifest.json` registers one earlier QUIC v1 baseline and 15 Track 1 capture attempts imported from Yash's repository, each with a metadata record and SHA-256.
- The imported Track 1 corpus has 14 PCAP files with packet records and one empty 24-byte IPv6 PCAP header. The empty file is retained as a failed attempt, not treated as evidence or tool agreement.
- Run `make check` to validate hashes and referenced artifacts. Run `make lab-eval` with the Docker tools to create fresh analysis under ignored `results/reproduced/`; imported outputs are preserved.
- The current C++ CLI reads classic Ethernet PCAP and recovers five complete ClientHellos from each of `quic_chromium.pcap` and `quic_curl.pcap`. The user reports all ten recovered byte strings match TShark 4.6.4 `tls.handshake_raw` values by set equality in Ubuntu WSL; raw exports and comparison script are not yet retained here. The first-stage flow grouping is DCID-scoped and is not a complete bidirectional/migration model. The clean-capture comparison shows no L1 extraction gap; any original-contribution direction must be grounded in further measured conditions.
- `captures/keylogs/` is ignored. Do not commit TLS session secrets. No key logs were imported.
- New captures are written under ignored `captures/reproduced/` by `make lab-capture`; review packet counts, hashes, provenance, and privacy before registering them.

Track 1 evidence is provisional. See [`docs/track1-evidence-audit.md`](../docs/track1-evidence-audit.md) for the cross-checks, version differences, and incomplete T3/T6/T7 arms.
