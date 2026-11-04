# QUIC recovery candidate disposition and diagnostic audit

## Decision status

**QUIC extraction/recovery is rejected as the original contribution for the tested conditions.** The user-reported WSL impairment run matches C++ and TShark on all retained complete ClientHellos across the six tested cases for each trace. In every-third-drop cases, the reference itself contains only two ClientHellos; that is conditional agreement on the surviving handshakes, not recovery of all five originals. The user-reported damaged-flow audit shows three explicit incomplete statuses per trace. Baseline correlation confirms no suffix gap for the unknown-length curl flow and an unreported-by-design suffix `[1026,1891)` for the unknown-length Chromium flow; the damaged capture lacks the handshake length header, so the CLI correctly labels its ranges observed-extent-only. This bounded correctness check shows no material diagnostics contribution gap. L1's clean-capture visibility gap is not supported. The primary contribution candidate is now L3 capture-vantage/proxy-aware JA4T attribution; its hypothesis, evidence gates, and first WSL commands are in [`l3-contribution-plan.md`](l3-contribution-plan.md). L3 is still provisional and must not be presented as a finding until its raw packet evidence is reproduced.

Do not describe the standards-defined QUIC Initial key derivation, classic-PCAP reading, or the clean-trace match as the original contribution. First establish a reproducible gap under a measured capture condition and show an improvement over a declared baseline.

## QUIC research question evaluated (not the active contribution candidate)

> Under controlled packet-capture degradation, how do QUIC v1 ClientHello recovery tools differ in exact-byte recall and in distinguishing incomplete evidence from unsupported or undecryptable traffic?

The evaluated direction was a **capture-quality-aware QUIC Initial recovery and completeness-diagnostics pipeline**. Recovery is rejected for the tested regimes; only a measured diagnostic classification gap could reopen that narrow question. Do not interpret this as the active contribution direction.

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

### User-reported damaged-flow diagnostic audit (commit `682051e`; baseline correlation reported 5 November 2026)

The user reports `make build` and `make test` passed in Ubuntu WSL (CTest 1/1, pytest 27/27) and mapped the every-third-drop frame selections to the C++ per-DCID output. The selected original frame numbers were curl `[3,31,60,65,94,120]` and Chromium `[3,29,56,59,85,113]`. For each trace, two original ClientHellos remained complete and three were explicitly labeled `client_hello=incomplete`; all three had decrypted CRYPTO data and no decrypt/frame/reassembly errors. The reported missing ranges were:

- **curl:** two flows declared 1509 expected bytes and reported `[1158,1509)`; the third reported `expected_bytes=unknown`, observed extent 1509, and `[0,1158)` within that extent. In the 5 November follow-up, the user maps this DCID to the 1509-byte clean-baseline ClientHello; no suffix is missing.
- **Chromium:** two flows declared 1884/1891 expected bytes and reported `[56,1000)` and `[70,1018)`; the third reported `expected_bytes=unknown`, observed extent 1026, and `[0,78)` within that extent. In the 5 November follow-up, the user maps this DCID to the 1891-byte clean-baseline ClientHello, so the baseline comparison additionally identifies missing suffix `[1026,1891)` that the damaged capture alone cannot infer.

The `observed_extent_only` scope is correct: for the unknown-length flows, the extractor reports only gaps detectable from that damaged capture and does not invent a total handshake length. The baseline-assisted Chromium suffix is an external comparison result, not a falsely claimed C++ observation. The user-reported audit therefore finds no material diagnostic classification gap in these cases. Frame lists and raw logs remain user-reported and are not retained here.

The same run exposed an evaluation-pipeline issue: in this TShark `-T jsonraw` output, repeated `tls.handshake_raw` members can appear at the same object level. Python's default `json.loads()` keeps only the last value for a duplicate object key, so the initial harness could silently lose earlier ClientHellos (the baseline reference count became zero). Commit `fec3b11` scans the raw export text to preserve all matching values. This is a **tooling/data-ingestion finding**, not evidence of a QUIC extractor limitation or an original protocol contribution. The wording should be scoped to this observed TShark JSON output, not generalized to every JSON parser or dissector. A duplicate-key regression test is committed and passes in the current expanded 36-test Python suite; the added L3 tests have not yet been run in the user's WSL environment.

### Decision and next gate

Do **not** pursue QUIC recovery or completeness diagnostics as the contribution on these results. The user reports three incomplete statuses per trace with explicit ranges and no decrypt/frame/reassembly failures. Baseline correlation identifies the Chromium suffix `[1026,1891)` that cannot be inferred from the damaged capture because its handshake header is absent; the extractor labels that uncertainty instead of fabricating an expected length. No material diagnostic classification gap was demonstrated.

L3 is now the primary candidate to investigate, but it is **not yet a final contribution claim**. Reproduce the targeted SYN/segment/frame measurements at documented capture points and resolve the T3 narrative-versus-aggregate discrepancy using raw packet evidence. Separate TCP termination/vantage effects from TSO/GSO segmentation effects; see `docs/l3-contribution-plan.md`. Do not describe an MSS outlier alone as proof of a proxy or of JA4T corruption.

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

### Diagnostic-only continuation gate

Reopen only the damaged-flow diagnostics question if the frame-to-flow audit demonstrates a reproducible, material misclassification or silent absence, and a scoped diagnostic change improves attribution without false-complete results. Otherwise keep QUIC recovery/diagnostics out of the original-contribution claim and continue with the L3 candidate in `docs/l3-contribution-plan.md`. Check prior art and the course rubric with the team before promoting any candidate to a final contribution.

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
- L3 capture-vantage/JA4T proxy-aware attribution is the primary candidate to investigate; it remains unverified until raw SYN evidence and the narrative/aggregate mismatch are resolved. See `docs/l3-contribution-plan.md`.
- L2, L6, and the L7 DoH arm still have missing or incomplete evidence.
