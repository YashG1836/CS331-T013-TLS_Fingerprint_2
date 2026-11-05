# Track 2 reproducible audit artifacts

## WSL verification batch

The user-run batch at `verification-batch-20261104-201936/` was generated on Ubuntu WSL at source commit `619a694a9fe449d97b4a54e487f0db7254b1fc08` and added to this branch in `00f34e4`. It contains environment/preflight, manifest and test logs, source/script hashes, QUIC Initial DCID inventory, SYN analysis, and six deterministic impairment cases for each of the Chromium and curl traces, including variants, TShark raw exports, logs, and result JSON. Its SHA256 manifest passed from the repository root; the relevant JSON parsed successfully in this checkout.

The WSL execution is user-run evidence, not a run independently reproduced in Arena. For each client, the six case comparisons report 27/27 exact-byte matches with TShark output on the same PCAP variant, no misses/extras; the every-third-drop arm is 2/2 in both tools. This is comparator agreement for bounded cases, not external ground truth. See `../../results/verification-status.md`, `../../docs/planning/DECISIONS.md`, and `../../LEDGER.md` for interpretation.

Do not edit or overwrite the committed batch. New runs should use a new timestamped directory from `code/scripts/verify_submission_batch.sh`, reviewed for provenance and privacy first.

## Related QUIC artifacts

- `quic-initial-dcid-inventory.json` at the parent Track 2 results directory is generated from the two committed classic-PCAP QUIC v1 captures. It preserves source PCAP hashes, packet record numbers, UDP endpoints, Initial DCIDs/SCIDs, and per-flow summaries. It is a derived header inventory, not decrypted payload evidence. Five later client Initial packets per trace use switched DCIDs matching server Initial SCIDs; these are not server-direction decrypt attempts.
- Earlier exact-byte `tls.handshake_raw` exports and the direct clean-capture comparison script are distinct from the batch's raw `jsonraw` case outputs and are not preserved as a separate export. The batch nonetheless includes per-case TShark raw outputs and the comparison metrics used for its bounded matrix.

## L3 paired-probe evidence

The report in `l3-paired-probe-c28a486.md` is a user-transcribed summary; the original paired-probe PCAPs/JSON were not supplied. It reports an inner container handshake missing from WSL `eth0`; it does not establish the suspected Windows/utility-VM path. The WSL batch's offload SYN analysis uses two separate captures and does not pair them. Obtain synchronized Windows/host-side and container/bridge captures before making an outer-vantage or proxy-termination claim.

## Regeneration commands

The batch runner includes the QUIC inventory, SYN analysis, and impairment commands in a single run. For a standalone impairment evaluation, use:

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

Keep scratch output under ignored `results/reproduced/`. To promote evidence, use a new `results/track2/` subdirectory, retain raw source artifacts and hashes, document exact commands and versions, and review privacy before tracking. Never substitute a transcription for original packet or tool output.
