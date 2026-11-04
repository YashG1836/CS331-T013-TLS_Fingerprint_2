# One-pass WSL verification batch

To avoid separate back-and-forth for each small offline check, run the following once from the repository root in Ubuntu WSL, after pulling the current branch:

```sh
git pull --ff-only origin arena/0d29f32c-cs331-phase2
code/scripts/verify_submission_batch.sh
```

The script batches:

1. Environment/preflight snapshot, tracked-manifest check, and `make test` (C++ build/CTest plus pytest).
2. Hashes for the four source PCAPs and the scripts used.
3. QUIC v1 DCID/SCID packet-header inventory for both QUIC PCAPs.
4. TShark SYN/SYN-ACK summary for the separate imported offload-on/off PCAPs (it does not pair them).
5. Deterministic C++/TShark impairment evaluations for both QUIC traces (seed 331), including cases, variants, logs, JSON results, and output hashes.

All output goes to a newly created `results/track2/verification-batch-<timestamp>/` directory, which is tracked rather than hidden by `.gitignore`. The script does not stage or commit anything. Review the generated JSON/PCAPs and privacy implications first; then send the directory or commit it on this session branch. It needs the WSL C++ build dependencies and TShark on `PATH`. The user reports a successful run at commit `619a694` (manifest 16 captures; build with zero warnings; CTest 1/1; pytest 39/39; impairment recall 1.0) in `results/track2/verification-batch-20261104-201936/`. That output directory has not yet been transferred into this shared checkout, so those run results remain user-reported here.

## One coordinated Windows-side capture session

The latest user-reported run did not see the container flow on Ubuntu WSL `eth0`, so that interface is not the outer point for that probe. For the next run, first list Windows capture interfaces using elevated PowerShell and Wireshark `dumpcap`; start 45-second captures on the WSL/vEthernet-facing adapter and physical adapter at the same time. While they are running, run the controlled container/bridge probe from `docs/l3-contribution-plan.md`. This is one short coordinated capture session, not several sequential experiments. The Windows interface IDs are machine-specific and must be selected from `dumpcap -D`.

Afterward, copy the original Windows PCAPNGs and the WSL container/bridge PCAPs into a tracked `results/track2/l3-paired-<run-id>/` directory with `sha256sum`, exact commands, interface descriptions, and tool versions. Run `l3_proxy_sanity.py` over the simultaneous observations, but create a pair manifest only after checking the same request and both handshake directions. Do not infer proxying from distinct TCP legs alone. Keep TSO/GSO toggle measurements separate.

## Human-required items

- `DECISIONS.md` is a working record and still requires team review/approval.
- `docs/landscape.md` is a scaffold, not a completed prior-art search.
- `ai/prompts.txt` is a partial log because the complete approved timestamped AI-use export was not supplied. Replace/augment it only with the actual export; do not reconstruct it.
- The raw WSL output from earlier runs is not in this checkout. A copied Markdown summary is not a substitute for the original JSON/PCAP evidence.
