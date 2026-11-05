# One-pass WSL verification batch

The batch runner produces a dated, tracked evidence directory without staging or committing files. The 4 November user-run WSL batch at `results/track2/verification-batch-20261104-201936/` predates the stateful mode. The updated runner was run in Ubuntu WSL on 5 November against source commit `fa9fcdb`; its results, logs, variant PCAPs, per-case JSON, and seven-row JSON are committed at `results/track2/verification-batch-20261105-105416/` (batch commit `03e89b8`). This makes the post-change output inspectable in this checkout, but does not make the WSL execution an independent Arena reproduction.

## What the batch records

1. Environment/preflight snapshot, tracked capture-manifest check, and `make test`.
2. Hashes for source PCAPs and scripts.
3. QUIC v1 DCID/SCID header inventory for the Chromium and curl PCAPs.
4. TShark SYN/SYN-ACK summaries for separate imported offload-on/off PCAPs; no cross-capture pairing is inferred.
5. Deterministic legacy and stateful C++/TShark impairment evaluations for both QUIC traces (seed 331), including cases, variant PCAPs, raw TShark exports, logs, directional/per-connection accounting, result JSON, and hashes. The 4 November batch is the earlier stateless matrix; the 5 November batch adds the stateful mode and exact baseline byte comparisons.
6. Seven-row artifact/live audit, plus an optional packet-bearing `[::1]` TLS control PCAP and metadata sidecar. The local capture is explicitly separate from public IPv6 egress.

## Recorded result snapshot

- Environment: TShark 4.6.4, GCC 15.2.0, OpenSSL 3.5.5, Python 3.14.4, Linux `6.18.33.2-microsoft-standard-WSL2`.
- Manifest: 16 capture records, 15 packet-bearing and one empty; all 16 remain provisional.
- Build/test: CTest 1/1; pytest 39/39; build log contains no warning output.
- Impairment: for each trace, six cases compare C++ output to TShark output on that same case's PCAP. All emitted reference ClientHellos match byte-for-byte as a multiset: 27/27 per trace; 54/54 total; zero misses and extras. Every-third-drop yields 2/2 in each tool per trace, not recovery of all five original ClientHellos. This is not independent ground truth or proof of broad QUIC correctness.
- Offload SYN analysis: each separate capture has three complete streams; client profile MSS/window-scale/window/TTL `1460/10/64240/64`, peer profile `65495/7/65408/63`. The analyzer says not to infer a proxy from one capture.

## Post-change 5 November result snapshot

The committed batch ran against `fa9fcdb` and recorded TShark 4.6.4, GCC 15.2.0, OpenSSL 3.5.5, Python 3.14.4, CTest **1/1**, and pytest **52/52**. In the stateful captured-order baseline, curl's 20 client Initial packets decrypt **20/20** (legacy DCID-keyed accounting: 10/20); Chromium's 16 decrypt **16/16** (legacy: 10/16). Each trace also has five server Initials, all decrypted, zero context misses, and five associations. The stateful baseline C++ ClientHello byte multisets match TShark 4.6.4 **5/5 per trace**, with zero misses/extras. The five alias buckets are distinct CID values; the 10/6 alias counts are packet records.

The stateful matrix is order-sensitive: reverse-record-order matches **0/5** in both traces and shuffle matches **4/5** in both; drop-one and truncate match 5/5, while every-third-drop matches 2/2 (TShark produces two references for those mutated PCAPs). By contrast, the earlier stateless matrix remains 27/27 per trace across six cases. Thus byte-equivalence/no-recall-regression is supported for the captured-order stateful baseline only, not for reordered traces. Full per-case data and directional/per-connection rows are in `quic-stateful/{curl,chromium}/impairment-results.json`.

The seven-row artifact audit reports L1/L2/L3/L4/L5/L7 PASS and L6 public egress NOT_MEASURED. The optional `::1` live check failed because tcpdump produced no packet-bearing IPv6 PCAP; the JSON therefore has overall live status FAIL. The WSL uplink was reported to lack global IPv6 routing. Do not summarize this as a clean overall live pass or as an IPv6 egress measurement.

See `results/verification-status.md`, `docs/planning/DECISIONS.md`, and `LEDGER.md` for evidence provenance, comparisons, and caveats. Keep the raw output directory immutable after review; run a fresh batch into a new timestamped directory rather than overwrite it.

## Re-run command

From the repository root in Ubuntu WSL, after pulling the current branch and checking the local worktree:

```sh
git pull --ff-only origin arena/0d29f32c-cs331-phase2
code/scripts/verify_submission_batch.sh
```

The script requires the WSL C++ build dependencies, OpenSSL development headers, and TShark on `PATH`. It now runs both legacy and stateful QUIC modes and the seven-row verifier with a local-loopback capture attempt. The 5 November run is archived; it records CTest 1/1 and pytest 52/52. To repeat after code changes, run the command above into a fresh timestamped directory. The runner does not stage or commit generated files. Review privacy and file sizes before committing a new batch.

## Seven-row verifier and tests

Run `python3 code/scripts/verify_all_seven_rows.py` for the standard-library artifact audit. It does not invoke CMake/TShark/capture tools and writes the structured seven-row summary to `results/reproduced/seven_rows_verification/summary.json`. The summary keeps the artifact audit (`rows`) separate from fresh tool work (`live_checks`) and records per-row `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, or `NOT_MEASURED` states with provenance and scope.

Run `python3 code/scripts/verify_all_seven_rows.py --live` to attempt a CMake build/current C++ QUIC extractor run on both traces and fresh TShark re-dissections for L2–L5 and L7. These runs use committed PCAPs, so they are fresh analyses of imported captures, not new network captures or independent ground truth. Missing tools are reported as `BLOCKED`; parse/count/value mismatches are `FAIL`. The L2 run uses an explicitly empty temporary TLS key-log file and tests the keyless visibility boundary; keyed output remains an audit of the imported result because no key log is supplied in the repository. The L3 run re-dissects both saved captures but does not toggle offload or establish a cross-vantage proxy boundary.

Run `python3 code/scripts/verify_all_seven_rows.py --ipv6-loopback` to attempt a real TLS exchange captured on local `[::1]` using `tcpdump`, a temporary self-signed certificate, and TShark JA4 extraction. The packet-bearing PCAP is now preserved under `results/reproduced/seven_rows_verification/ipv6-loopback/` by default, with a SHA256-bearing metadata sidecar; pass `--ipv6-loopback-output-dir PATH` to choose a run-specific location and `--output PATH` to save the summary alongside it. Temporary certificate/key files are not preserved. This proves only the local IPv6 capture/extraction path—not global routing or public IPv6 egress. The committed 24-byte L6 PCAP remains empty and is still independently reported as `NOT_MEASURED` for public-egress evidence. `--live --ipv6-loopback` requests both sets of checks.

For an actual public-egress capture, use a dual-stack uplink with working global IPv6 and run the Linux helper from the repository root, e.g. `sudo code/scripts/capture_ipv6_egress.sh "results/track2/l6_ipv6_$(date -u +%Y%m%dT%H%M%SZ)" example.com`. It records route/interface/address and tool versions, direct `curl -6` and same-host `curl -4` results (without proxy use), packet captures, SYN and ClientHello TShark extracts, and a SHA256 manifest. A missing route, non-global source, failed TLS, or absent ClientHello yields `NOT_MEASURED`/nonzero exit and retained diagnostic logs; it never turns lack of connectivity into a pass. `CAPTURED_REVIEW_REQUIRED` means a public IPv6 ClientHello was captured, not that the IPv6/IPv4 difference has been explained. Review the target addresses, route, capture point, and paired output; endpoint/CDN/path differences remain possible. If WSL has no global route, repeat from a genuinely IPv6-capable uplink (for example, another Wi-Fi/hotspot or a native Linux host). A `::1` capture is only a local control.

An artifact `PASS` means only that the stated checks passed at their existing provenance level; it does not convert imported/team-supplied results into fresh measurements or establish novelty. The overall artifact status remains `INCOMPLETE` while L6's public-IPv6 measurement is absent, even if local-loopback capture succeeds. The JSON separately records whether requested live checks passed, failed, were blocked, or were not requested.

The automated test exercises each of the seven artifact rows and validates the seven-row/live JSON schema without depending on optional tools or external connectivity. Run with pytest where installed, or with the standard library as `python3 -m unittest discover -s code/scripts/tests -p 'test_seven_rows_verification.py' -v`.

## Remaining gates after the evidence archive

The 5 November batch now preserves tool versions, build/CTest/pytest logs, source hashes, stateful stdout/JSON, per-direction and per-connection counts, TShark raw exports, and exact baseline byte-multiset comparisons. The remaining evidence/interpretation gates are:

- The stateful `reverse-record-order` and `shuffle-record-order` misses must remain visible in any report; the claimed byte preservation is for original captured order only. Do not present a blanket order-independent recall claim.
- Public IPv6 L6 remains `NOT_MEASURED`. To measure it, run `code/scripts/capture_ipv6_egress.sh` on a dual-stack uplink with a global route, then review the endpoint address, capture point, PCAP, TShark extracts, and hashes. A `::1` control is not a substitute.
- The separate earlier `tls.handshake_raw` export/script is still not retained as a standalone artifact; the current batch contains TShark `jsonraw` outputs for its recorded cases.
- Independent Arena reproduction, targeted prior-art review, course-rubric assessment, and team approval are still open. Do not infer them from WSL test success or the batch results.

## Human-required items

- Team review/approval of `docs/planning/DECISIONS.md`, the contribution choice, and final wording remains open.
- `docs/landscape.md` is a sourced comparative survey, not a completed comprehensive prior-art search.
- `ai/prompts.txt` remains partial because the full approved timestamped AI-use export was not supplied; do not reconstruct it.
- The L3 run now has a Wi-Fi adapter capture, a vEthernet capture, container `eth0`, and WSL `eth0`; the bridge attempt failed and there is no physical-wire tap. Keep the intermediate mechanism unresolved; a native-Linux or successfully captured bridge-vantage control may be needed for attribution.
