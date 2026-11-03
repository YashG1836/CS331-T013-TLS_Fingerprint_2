# Experiment scripts

Python code here orchestrates external tools, validates the capture manifest, computes statistics, and emits generated report data. Scripts must not hand-author experimental numbers. Add each capture and its reproduction commands to `captures/manifest.json` before reporting a result.

Current scripts:

- `preflight.py` records CMake/compiler/OpenSSL, TShark and FoxIO JA4+ versions, capture interfaces, and actual TShark QUIC/fingerprint fields. It does not capture packets or claim results.
- `reference_baseline.py` runs FoxIO JA4+ and TShark on one registered pcap and records the capture hash, exact commands, versions, field availability, exit status, and raw outputs. It does not interpret differences or claim a limitation.
- `evaluate.py` validates the manifest and emits a corpus-status summary. Statistical comparison and generated report tables remain unimplemented until real evidence is registered.
