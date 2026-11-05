# Capture corpus

- `captures/manifest.json` registers one earlier QUIC v1 baseline and 15 Track 1 capture attempts imported from Yash's repository, each with a metadata record and SHA-256.
- The imported Track 1 corpus has 14 PCAP files with packet records and one empty 24-byte IPv6 PCAP header. The empty file is retained as a failed attempt, not treated as evidence or tool agreement.
- Run `make check` to validate hashes and referenced artifacts. Run `make lab-eval` with the Docker tools to create fresh analysis under ignored `results/reproduced/`; imported outputs are preserved.
- The classic-PCAP C++ CLI has a legacy DCID-keyed mode and a bounded `--stateful-initial-context` mode. The committed 5 November WSL batch at `results/track2/verification-batch-20261105-105416/` records 5/5 exact ClientHello byte-multiset matches against TShark 4.6.4 for each captured-order stateful baseline and full per-case `jsonraw` outputs. The separate earlier `tls.handshake_raw` export/script is not retained. The stateful association uses a fixed UDP 4-tuple and is order-sensitive (reverse-order 0/5; shuffle 4/5 per trace); it is not complete CID migration support. The clean baseline shows no ClientHello recall gap; see `docs/quic/implementation-status.md` and `results/verification-status.md`.
- `captures/keylogs/` is ignored. Do not commit TLS session secrets. No key logs were imported.
- New captures are written under ignored `captures/reproduced/` by `make lab-capture`; review packet counts, hashes, provenance, and privacy before registering them.

Track 1 evidence is provisional. See [`docs/track1-evidence-audit.md`](../docs/track1-evidence-audit.md) for the cross-checks, version differences, and incomplete T3/T6/T7 arms.
