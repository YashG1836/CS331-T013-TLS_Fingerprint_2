# Ubuntu / WSL and Docker setup

Two imported tool snapshots are intentionally kept separate:

- `results/preflight.json`: the earlier team WSL environment (TShark 4.6.4, JA4 reporting 0.18.6).
- `results/versions.txt`: Yash's Docker lab (TShark 4.4.19, the v0.18.6 JA4 tag reporting 0.18.5, plus an optional unreleased `ja4-main`).

The new Track 1 `results/checkpoint_build_test.txt` reports a build/test of the modular C++ code, but does not record the exact source SHA. `results/verification-status.md` separately describes the earlier monolithic archive log. Treat each imported record according to its source; neither replaces current branch CI.

## Core build and tests on Ubuntu/WSL

```sh
sudo apt update
sudo apt install -y build-essential cmake libssl-dev python3 python3-venv make
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

make test PYTHON=python
make check PYTHON=python
make eval PYTHON=python
```

To record local readiness without overwriting the imported WSL snapshot:

```sh
make preflight PYTHON=python
```

This writes `results/preflight-current.json`. TShark and JA4 are not needed for the C++/pytest tests, but are needed for fresh reference-tool analysis.

## QUIC extractor and independent raw reference

To reproduce the current C++ extraction and capture complete CLI output locally:

```sh
make build
mkdir -p results/reproduced
build/code/quic/src/quic-fingerprint --pcap captures/pcaps/quic_chromium.pcap > results/reproduced/quic_chromium_extractor.txt
build/code/quic/src/quic-fingerprint --pcap captures/pcaps/quic_curl.pcap > results/reproduced/quic_curl_extractor.txt
```

For an independent TShark reference in Ubuntu/WSL, install TShark if needed and save raw dissections outside the repository:

```sh
sudo apt install -y tshark
tshark -r captures/pcaps/quic_chromium.pcap -Y 'tls.handshake.type == 1' -T jsonraw > /tmp/quic_chromium-clienthellos.json
tshark -r captures/pcaps/quic_curl.pcap -Y 'tls.handshake.type == 1' -T jsonraw > /tmp/quic_curl-clienthellos.json
```

The user reports completing this check on Ubuntu WSL with TShark 4.6.4 using its `tls.handshake_raw` field: all five values per capture matched the C++ output as unordered byte-string sets. The raw exports, exact command, and comparison script are not yet retained in the repository. To make the reported pass reproducible, preserve those artifacts (or privacy-reviewed hashes and a comparison summary) and record the TShark version. If you rerun, compare full handshake bytes, not only lengths or fingerprint hashes; use an export path that retains reassembled TLS handshake bytes.

## Track 1 Docker lab

With Docker installed and network access for the image build:

```sh
make lab-image
make lab-eval
```

The image pins the JA4 release tag and the `ja4-main` comparison commit, and installs TShark, tcpdump, Chromium, curl, and supporting tools. `make lab-eval` reads the committed capture set without generating traffic and writes fresh results under ignored `results/reproduced/`. It does not overwrite the imported summary or raw files.

Only generate new network traffic when authorized and needed:

```sh
make lab-capture CAPTURE_ID=quic_chromium
```

This requires network access and writes under ignored `captures/reproduced/`; it does not register a new evidence record. Review the output and add metadata/hash only after confirming packet count, provenance, and sensitivity. Keep TLS key logs local and uncommitted.
