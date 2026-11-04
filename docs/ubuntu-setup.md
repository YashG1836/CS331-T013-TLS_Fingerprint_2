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

The committed WSL batch at `results/track2/verification-batch-20261104-201936/` preserves per-case TShark `jsonraw` exports, C++ output logs, commands, variants, and comparison metrics for the bounded impairment matrix. It reports exact-byte equality on those cases, but the WSL run was not independently regenerated in Arena. The earlier standalone `tls.handshake_raw` export/script is not saved separately. If you rerun, compare full handshake bytes, not only lengths or fingerprint hashes; retain reassembled TLS handshake bytes, raw outputs, exact commands, and TShark version.

### Controlled impairment matrix

After the build and clean-reference check, run the deterministic harness on both sources. It uses TShark to select Initial records carrying CRYPTO and writes only to the ignored work directories; it does not edit the committed captures.

```sh
python3 code/scripts/quic_impairment.py \
  --input captures/pcaps/quic_chromium.pcap \
  --work-dir results/reproduced/quic_impairment/chromium \
  --extractor build/code/quic/src/quic-fingerprint --tshark tshark --seed 331

python3 code/scripts/quic_impairment.py \
  --input captures/pcaps/quic_curl.pcap \
  --work-dir results/reproduced/quic_impairment/curl \
  --extractor build/code/quic/src/quic-fingerprint --tshark tshark --seed 331
```

Each run compares the current C++ extractor and TShark on the same clean and mutated PCAPs: reverse order, fixed-seed shuffle, drop one/every third TShark-identified Initial CRYPTO-carrying record, and truncate the captured tail of one such record by 64 bytes. It prints exact-byte recall, missed/extra handshakes, and saves per-case commands, hashes, logs, and details to `impairment-results.json`. Inspect `cases.json` to see which frames were selected. If TShark 4.6.4 formats `quic.long.packet_type` or the display filter differently, stop and report the error rather than relabeling a different packet as Initial.

### Incomplete-flow/missing-range audit

After updating the branch and rebuilding, the extractor reports each incomplete DCID, the expected ClientHello byte length when its four-byte handshake header is present, the observed CRYPTO extent, and missing half-open ranges `[start,end)`. If the header itself is missing, it marks the range scope as `observed_extent_only`; a missing suffix cannot be known without the declared total length. Re-run the exact every-third-drop variants from the existing reproduction directory and save a privacy-minimized summary (the filter below excludes ClientHello hex):

```sh
set -o pipefail
make build && make test
mkdir -p results/reproduced/quic_impairment/diagnostic-audit
for name in curl chromium; do
  pcap="results/reproduced/quic_impairment/${name}/variants/drop-every-third-initial-crypto-record.pcap"
  build/code/quic/src/quic-fingerprint --pcap "$pcap" 2>&1 \
    | grep -E '^(pcap_|non_matching_destination_port=|flow_dcid=|client_hello=|client_hello_expected_bytes=|crypto_observed_extent_bytes=|crypto_missing_ranges_scope=|crypto_missing_ranges=|complete_client_hellos=)' \
    > "results/reproduced/quic_impairment/diagnostic-audit/${name}.txt"
done
```

Compare each flow's status/range with the original frame list in that case's `cases.json` and this source-packet map (the latter prints all QUIC CRYPTO rows; use the packet-type field to select Initial rows):

```sh
for name in curl chromium; do
  tshark -r "captures/pcaps/quic_${name}.pcap" \
    -Y 'quic.crypto.length > 0' -T fields \
    -E header=y -E separator=$'\t' -E occurrence=a -E aggregator=, \
    -e frame.number -e quic.long.packet_type -e quic.dcid \
    -e quic.crypto.offset -e quic.crypto.length \
    > "results/reproduced/quic_impairment/diagnostic-audit/${name}-crypto-frames.tsv"
done
```

The expected ClientHello set on the mutated capture is not the original five: the reported every-third-drop reference retained only two. Do not call `2/2` recovery of all five.

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
