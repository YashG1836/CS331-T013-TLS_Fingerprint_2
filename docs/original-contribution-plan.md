# Original-contribution scaffold: QUIC capture-quality recovery

## Decision status

**No recovery gap demonstrated; diagnostic gap still unmeasured.** The user-reported WSL impairment run matches C++ and TShark on all retained complete ClientHellos across the six tested cases for each trace. This is negative evidence against an extraction/reordering/loss/truncation contribution in these conditions. Do not relabel a match with the mutated TShark output as recovery of all original handshakes: in the every-third-drop cases, the reference itself contains only two ClientHellos. A narrow completeness-diagnostics contribution remains only a hypothesis until the per-flow dispositions are checked against the known mutations. L1's clean-capture visibility gap is not supported.

Do not describe the standards-defined QUIC Initial key derivation, classic-PCAP reading, or the clean-trace match as the original contribution. First establish a reproducible gap under a measured capture condition and show an improvement over a declared baseline.

## Provisional research question

> Under controlled packet-capture degradation, how do QUIC v1 ClientHello recovery tools differ in exact-byte recall and in distinguishing incomplete evidence from unsupported or undecryptable traffic?

The candidate engineering direction is a **capture-quality-aware QUIC Initial recovery and completeness-diagnostics pipeline**. The possible contribution would be limited to a demonstrated, reproducible improvement in a defined impairment regime—not a general claim that other tools fail.

## Baseline now available

- `quic_chromium.pcap`: five extracted ClientHellos, lengths 1884, 1891, 1885, 1891, and 1880 bytes.
- `quic_curl.pcap`: five extracted ClientHellos, each 1509 bytes.
- The user reports that all ten C++ handshake byte strings match TShark 4.6.4 `tls.handshake_raw` values by set equality. TShark packet-arrival order differs from the CLI's DCID iteration order, so the reported comparison is set-based rather than positional.
- User-reported WSL environment: TShark 4.6.4, GCC 15.2.0, OpenSSL 3.5.5. The raw exports, exact commands, and comparison script have not yet been committed, so this result is recorded as user-reported, not independently reproduced in Arena.
- The CLI reports ten candidate Initial DCIDs and five decrypt failures per capture while still recovering all five TShark ClientHellos. Those failures are **not** evidence of five missed ClientHellos; classify their packets before treating them as a gap.

## User-reported impairment results (4 November 2026)

The user reports running commit `fec3b11` on Ubuntu WSL with TShark 4.6.4 and seed 331. The reported C++-versus-TShark exact-byte comparison was:

| Variant | curl reference / extracted / matched | Chromium reference / extracted / matched |
|---|---:|---:|
| Baseline | 5 / 5 / 5 | 5 / 5 / 5 |
| Reverse record order | 5 / 5 / 5 | 5 / 5 / 5 |
| Seeded record shuffle | 5 / 5 / 5 | 5 / 5 / 5 |
| Drop one selected Initial CRYPTO record | 5 / 5 / 5 | 5 / 5 / 5 |
| Drop every third selected Initial CRYPTO record | 2 / 2 / 2 | 2 / 2 / 2 |
| Truncate 64 captured bytes from selected record | 5 / 5 / 5 | 5 / 5 / 5 |

The user reports zero misses and extras in every mutated-reference comparison, and no false-complete outputs. The 2/2 result in the every-third-drop case is **conditional recall against TShark's mutated-capture output**, not five-of-five recovery against the original clean trace. These results establish no extraction gap against TShark for this limited deterministic matrix. They do not establish broad QUIC robustness, nor independently prove either tool's correctness; the raw `impairment-results.json`, case manifests, and logs have not been retained here and the TShark runs have not been independently rerun in this environment.

The same run exposed an evaluation-pipeline issue: in this TShark `-T jsonraw` output, repeated `tls.handshake_raw` members can appear at the same object level. Python's default `json.loads()` keeps only the last value for a duplicate object key, so the initial harness could silently lose earlier ClientHellos (the baseline reference count became zero). Commit `fec3b11` scans the raw export text to preserve all matching values. This is a **tooling/data-ingestion finding**, not evidence of a QUIC extractor limitation or an original protocol contribution. The wording should be scoped to this observed TShark JSON output, not generalized to every JSON parser or dissector. A regression test is now added locally to ensure both repeated values survive.

### Decision and next gate

Do **not** pursue QUIC recovery improvements on these results. First time-box a diagnostics audit using the saved `impairment-results.json` from both traces: map each removed/truncated PCAP record to its DCID/CRYPTO range and expected affected ClientHello, then inspect whether C++ reports each broken flow as incomplete (rather than decrypt-failed, unsupported, or silently absent). Compare with TShark as a reference, but treat the mutation manifest and known source flows as the primary expected-outcome record. Only scope diagnostic reporting as the contribution if this reveals a material, reproducible classification gap and a change improves it without false-complete results.

If no such gap exists, reject the QUIC contribution candidate rather than inventing one. L3 TCP vantage/JA4T proxy sanity checks are the fallback, but they are **not ready to become the contribution yet**: reproduce the targeted SYN/segment/frame measurements and resolve the existing T3 narrative-versus-aggregate discrepancy using raw packet-level evidence. Do not pursue both arms as simultaneous contribution claims.

## Measurement plan before claiming a contribution

### Inputs and controls

1. Preserve the two clean PCAPs as immutable baselines; record hashes and the exact reference/export commands.
2. Save TShark's reassembled ClientHello bytes, tool version, and C++ output for each clean baseline. Include a deterministic comparison script that compares byte strings without assuming output order.
3. Run both the current C++ CLI and TShark 4.6.4 on deterministic, derived PCAPs. Never overwrite the committed source captures; keep mutations and outputs under ignored reproduction directories until reviewed.

### Controlled conditions

- Clean capture control.
- Reverse packet-record order and a fixed-seed packet-record shuffle.
- Remove selected UDP records, including records carrying Initial CRYPTO data; record the exact removed frame numbers and hashes.
- Create selected snap-length/truncation variants while preserving valid PCAP record framing.
- Add a separate synthetic unsupported-link/IP-header case to verify that unsupported input is reported rather than misclassified as an incomplete ClientHello; the current mutation harness does not generate that case yet.

For each condition, compare tools on the same mutated bytes. Do not assume TShark is ground truth for every impairment without checking its own output and failure behavior.

### Metrics

- Reference ClientHello count and exact-byte recovery count.
- Exact-byte recall: `byte-identical recovered ClientHellos / reference ClientHellos`.
- False-complete count (the extractor emits a byte sequence that is not a complete reference ClientHello).
- Incomplete, decrypt-failed, parse-failed, and unsupported dispositions, with packet/frame counts and missing CRYPTO ranges where measurable.
- Runtime may be recorded, but is not a novelty result by itself.

### Decision gate

Continue this candidate only if a controlled condition produces a reproducible, material gap in the current implementation or the reference workflow, and a scoped change measurably improves exact-byte recovery or failure diagnosis without introducing false-complete results. Otherwise reject this candidate and reassess alternatives using the reconciled L2–L7 evidence. Check prior art and the course rubric with the team before promoting any candidate to the final contribution.

## Scaffolded implementation and commands

`code/scripts/quic_impairment.py` now provides the first deterministic mutation/evaluation harness. It leaves source PCAPs untouched, uses TShark's `quic.crypto.length` and `quic.long.packet_type` fields to locate Initial CRYPTO-carrying records, records input/variant hashes and exact tool argv, then compares complete ClientHello byte-string multisets from the C++ CLI and TShark on each variant. It generates: clean baseline, reverse record order, fixed-seed shuffle, drop one median Initial-CRYPTO record, drop every third such record, and truncate the captured tail of the median record (64 bytes by default). Logs and raw TShark JSON are written under the ignored work directory.

Run after `make build` and installing TShark:

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

Each run writes `cases.json`, per-case extractor/TShark logs, and `impairment-results.json` with exact-byte recall, missed/extra outputs, incomplete flows, decryption failures, and tool return codes. It exits nonzero on a tool/comparison error. Inspect the selected frame numbers in `cases.json`; the automated cases target TShark-identified Initial CRYPTO records, but verify the chosen frames and mutation semantics before interpreting results. Keep these raw experiment artifacts under ignored `results/reproduced/` unless reviewed for privacy and deliberately curated.

1. Retain the user's clean-capture raw reference export/command/script or a reviewed hashed summary.
2. Run the deterministic impairment matrix and compare both tools on identical bytes; do not treat TShark as infallible under impaired captures.
3. Extend C++ reporting only if measurements identify a missing disposition or recovery behavior; avoid speculative feature work.
4. Evaluate controlled cases, publish failures as well as successes, then decide whether the contribution is novel and course-appropriate.

## Alternatives not selected at this stage

- L1 reference-tool coverage is not supported by the current clean-trace results.
- L5's reported released-versus-unreleased JA4 difference is not a clean contribution candidate until the missing `ja4-main` raw results and source/build provenance are reproducible; the reported issue is already fixed upstream.
- L3 JA4T/MSS capture-vantage analysis remains blocked on the narrative/aggregate mismatch and missing raw SYN evidence.
- L2, L6, and the L7 DoH arm still have missing or incomplete evidence.
