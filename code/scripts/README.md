# Experiment scripts

Python code here orchestrates external tools, validates the capture manifest, computes statistics, and emits generated report data. Scripts must not hand-author experimental numbers. Add each capture and its reproduction commands to `captures/manifest.json` before reporting a result.

Current scripts:

- `preflight.py` records CMake/compiler/OpenSSL, TShark and FoxIO JA4+ versions, capture interfaces, and actual TShark QUIC/fingerprint fields. `make preflight` writes `results/preflight-current.json`; the imported team snapshot remains at `results/preflight.json`. It does not capture packets or claim results.
- `reference_baseline.py` runs FoxIO JA4+ and TShark on one registered pcap and records the capture hash, exact commands, versions, field availability, exit status, and raw outputs. It does not interpret differences or claim a limitation.
- `evaluate.py` validates capture hashes, metadata, and artifact paths, then emits a conservative corpus-status summary. The current record is provisional; statistical comparison and final report tables remain unimplemented.
