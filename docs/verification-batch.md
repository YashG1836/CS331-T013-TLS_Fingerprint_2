# One-pass WSL verification batch

The batch runner produces a dated, tracked evidence directory without staging or committing files. It was run by the user from Ubuntu WSL at commit `619a694a9fe449d97b4a54e487f0db7254b1fc08` on the active branch, timestamp `2026-11-04T20:19:36Z`. The resulting artifacts are now present at `results/track2/verification-batch-20261104-201936/` (added by commit `00f34e4`). The SHA256 manifest passed from the repository root; relevant JSON parsed successfully. This makes the outputs inspectable, but does not make the WSL run an independent Arena reproduction.

## What the batch records

1. Environment/preflight snapshot, tracked capture-manifest check, and `make test`.
2. Hashes for source PCAPs and scripts.
3. QUIC v1 DCID/SCID header inventory for the Chromium and curl PCAPs.
4. TShark SYN/SYN-ACK summaries for separate imported offload-on/off PCAPs; no cross-capture pairing is inferred.
5. Deterministic C++/TShark impairment evaluations for both QUIC traces (seed 331), including cases, variant PCAPs, raw TShark exports, logs, result JSON, and hashes.

## Recorded result snapshot

- Environment: TShark 4.6.4, GCC 15.2.0, OpenSSL 3.5.5, Python 3.14.4, Linux `6.18.33.2-microsoft-standard-WSL2`.
- Manifest: 16 capture records, 15 packet-bearing and one empty; all 16 remain provisional.
- Build/test: CTest 1/1; pytest 39/39; build log contains no warning output.
- Impairment: for each trace, six cases compare C++ output to TShark output on that same case's PCAP. All emitted reference ClientHellos match byte-for-byte as a multiset: 27/27 per trace; 54/54 total; zero misses and extras. Every-third-drop yields 2/2 in each tool per trace, not recovery of all five original ClientHellos. This is not independent ground truth or proof of broad QUIC correctness.
- Offload SYN analysis: each separate capture has three complete streams; client profile MSS/window-scale/window/TTL `1460/10/64240/64`, peer profile `65495/7/65408/63`. The analyzer says not to infer a proxy from one capture.

See `results/verification-status.md`, `DECISIONS.md`, and `LEDGER.md` for evidence provenance, comparisons, and caveats. The raw output directory should remain immutable after review; run a fresh batch into a new timestamped directory rather than overwrite it.

## Re-run command

From the repository root in Ubuntu WSL, after pulling the current branch and checking the local worktree:

```sh
git pull --ff-only origin arena/0d29f32c-cs331-phase2
code/scripts/verify_submission_batch.sh
```

The script requires the WSL C++ build dependencies and TShark on `PATH`. It does not stage or commit generated files. Before adding a new run, review privacy and file sizes; preserve original commands, versions, source hashes, and the generated manifest.

## Human-required items

- Team review/approval of `DECISIONS.md`, the contribution choice, and final wording remains open.
- `docs/landscape.md` is a sourced comparative survey, not a completed comprehensive prior-art search.
- `ai/prompts.txt` remains partial because the full approved timestamped AI-use export was not supplied; do not reconstruct it.
- Raw Windows-host/outer captures for the L3 paired-vantage experiment are still missing. The current WSL batch does not contain them.
