# Experiment scripts

Python orchestrates experiment metadata and reference-tool runs; C++ remains the QUIC parsing/cryptography/reassembly core. Scripts must record exact argv, tool errors, and raw outputs. They must not hand-author experimental numbers.

- `preflight.py` records CMake/compiler/OpenSSL, TShark/FoxIO versions, interfaces, and actual TShark QUIC/fingerprint fields. `make preflight` writes `results/preflight-current.json`; the imported WSL snapshot remains at `results/preflight.json`.
- `reference_baseline.py` runs FoxIO JA4+ and TShark for the earlier single QUIC baseline and writes to `results/reference/`. It records output but does not interpret differences.
- `evaluate.py` validates the current capture manifest, hashes, metadata, packet-count status, and artifact paths. `make eval` emits corpus status only; it does not rerun tools or infer a limitation.
- `analyze.py` reruns the Track 1 multi-capture TShark/FoxIO analysis. `make lab-eval` writes fresh tool output under ignored `results/reproduced/`, never replacing imported `results/raw/` or `results/summary.*`.
- `capture.py` can recapture one reviewed Track 1 recipe only when explicitly invoked with `--confirm-network`. It writes to ignored `captures/reproduced/`, records command outcomes, and never overwrites committed evidence by default.
- `versions.sh` records the lab's exact tool versions; `make lab-versions` writes to ignored `results/reproduced/versions.txt`.
- `quic_impairment.py` creates deterministic record-order, Initial-CRYPTO loss, and snap-length-truncation PCAP variants, then compares complete ClientHello byte multisets from the C++ extractor and TShark. It records input/variant hashes, commands, raw logs, exact-byte recall, missed/extra outputs, and failure diagnostics. It preserves repeated `tls.handshake_raw` values from the observed TShark JSON output. Send `--work-dir` under ignored `results/reproduced/`; source captures are never modified.
- `quic_initial_inventory.py` writes a portable JSON inventory of QUIC v1 Initial headers in classic Ethernet PCAPs, including UDP endpoints and DCID/SCID changes. It does not decrypt payloads; the current audited output is committed under `results/track2/`.
- `l3_proxy_sanity.py` extracts per-stream TCP SYN/SYN-ACK profiles from one or more PCAPs and optionally compares manually paired streams. It does not calculate JA4T/JA4TS and never infers a proxy from MSS/TTL alone; use ignored output under `results/reproduced/l3/`.

The imported Track 1 analysis is team-supplied from a Docker environment and has not been rerun as a full suite. The user separately reports a TShark 4.6.4 byte-set comparison for the two QUIC PCAPs. See `docs/track1-evidence-audit.md` and `results/verification-status.md`.
