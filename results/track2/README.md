# Track 2 reproducible audit artifacts

- `quic-initial-dcid-inventory.json` is generated from the two committed classic-PCAP QUIC v1 captures by `code/scripts/quic_initial_inventory.py`. It preserves source PCAP SHA-256 values, packet record numbers, UDP endpoints, Initial DCIDs/SCIDs, and per-UDP-flow summaries. It is a derived header inventory, not a raw TShark export and not decrypted payload evidence.

The WSL impairment harness's original `cases.json`, `impairment-results.json`, TShark raw exports, and the recent paired-probe PCAP/JSON files are not available in this checkout. Do not reconstruct or label a transcribed summary as those raw artifacts. The user-reported measurements are documented with provenance in `results/verification-status.md`, `results/track2/l3-paired-probe-c28a486.md`, and `docs/l3-contribution-plan.md`.

To regenerate the impairment artifacts directly into a tracked location in WSL (after checking disk/privacy policy), use:

```sh
python3 code/scripts/quic_impairment.py \
  --input captures/pcaps/quic_chromium.pcap \
  --work-dir results/track2/quic-impairment/chromium \
  --extractor build/code/quic/src/quic-fingerprint --tshark tshark --seed 331

python3 code/scripts/quic_impairment.py \
  --input captures/pcaps/quic_curl.pcap \
  --work-dir results/track2/quic-impairment/curl \
  --extractor build/code/quic/src/quic-fingerprint --tshark tshark --seed 331
```

For a paired probe, copy the original PCAPs and original checker JSON from the ignored run directory into a uniquely named `results/track2/l3-paired-<run-id>/` directory, include a SHA-256 manifest and the exact commands/tool versions, then inspect `git status` and review packet/IP privacy before adding. Keep the Markdown transcription separate from the raw files. Do not commit TLS key logs or unrelated workstation data.
