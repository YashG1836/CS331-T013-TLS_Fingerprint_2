# Experiment scripts

Python orchestrates experiment metadata and reference-tool runs; C++ remains the QUIC parsing/cryptography/reassembly core. Scripts must record exact argv, tool errors, and raw outputs. They must not hand-author experimental numbers.

- `preflight.py` records CMake/compiler/OpenSSL, TShark/FoxIO versions, interfaces, and actual TShark QUIC/fingerprint fields. `make preflight` writes `results/preflight-current.json`; the imported WSL snapshot remains at `results/preflight.json`.
- `reference_baseline.py` runs FoxIO JA4+ and TShark for the earlier single QUIC baseline and writes to `results/reference/`. It records output but does not interpret differences.
- `evaluate.py` validates the current capture manifest, hashes, metadata, packet-count status, and artifact paths. `make eval` emits corpus status only; it does not rerun tools or infer a limitation.
- `analyze.py` reruns the Track 1 multi-capture TShark/FoxIO analysis. `make lab-eval` writes fresh tool output under ignored `results/reproduced/`, never replacing imported `results/raw/` or `results/summary.*`.
- `capture.py` can recapture one reviewed Track 1 recipe only when explicitly invoked with `--confirm-network`. It writes to ignored `captures/reproduced/`, records command outcomes, and never overwrites committed evidence by default.
- `versions.sh` records the lab's exact tool versions; `make lab-versions` writes to ignored `results/reproduced/versions.txt`.

The imported Track 1 outputs are team-supplied from a Docker environment; current TShark/FoxIO/Docker results have not been rerun in this checkout. See `docs/track1-evidence-audit.md`.
