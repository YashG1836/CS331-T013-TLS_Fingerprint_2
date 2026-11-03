# Ubuntu / WSL setup and verification

A team-supplied WSL preflight snapshot is preserved at `results/preflight.json`; it reports CMake 4.2.3, GCC 15.2.0, OpenSSL 3.5.5, TShark 4.6.4, tcpdump 4.99.6, Python 3.14.4, and a FoxIO `ja4` executable. A real QUIC v1 pcap and its team-supplied TShark/FoxIO outputs are now stored in the repository. The archived `make test` result, however, came from a separate source tree using a monolithic C++ file and GoogleTest; it does not validate this repository's modular C++ implementation. See `results/verification-status.md` for the caveats.

On a fresh Ubuntu/WSL checkout, install the modular project's dependencies:

```sh
sudo apt update
sudo apt install -y build-essential cmake libssl-dev python3 python3-venv make tshark tcpdump
```

Install pytest in a virtual environment and verify the current branch:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

git status --short --branch
make preflight PYTHON=python
make test PYTHON=python
make check PYTHON=python
make eval PYTHON=python
```

`make preflight` writes a fresh snapshot to `results/preflight-current.json`, preserving the imported team snapshot at `results/preflight.json`. Check that TShark is at least 4.0.6, that `ja4` is on `PATH`, and that the actual field listing includes the expected QUIC/JA3/JA4 abbreviations. Interface listing does not prove capture permissions; test the chosen interface with a one-second capture to `/dev/null` before an experiment.

For a fresh baseline run, use the capture already registered in the manifest:

```sh
make baseline CAPTURE_ID=quic-v1-initial-baseline-2026-11-03 PYTHON=python
```

The current runner will write to `results/reference/`. It will not overwrite the imported team outputs in `results/baseline/`. The stored outputs were generated with commands that differ from the current runner; provenance and rerun status are described in `docs/baseline-procedure.md`.

Capture only controlled, consented test sessions. Do not commit public-session TLS key logs, credentials, or unrelated personal traffic. Do not call the one matched JA4 value a confirmed limitation result; L1 remains provisional until the missing provenance and independent ClientHello-byte comparison are resolved.
