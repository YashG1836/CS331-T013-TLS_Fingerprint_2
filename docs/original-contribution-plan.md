# QUIC recovery candidate disposition and diagnostic audit

## Decision status

**Updated 5 November 2026 — the broad QUIC extraction/recovery and completeness-diagnostics hypothesis remains rejected; the narrower Initial-context/accounting result is now backed by a committed WSL batch.** The batch at `results/track2/verification-batch-20261105-105416/` was run against source commit `fa9fcdb`, and records CTest 1/1, pytest 52/52, TShark 4.6.4, per-case outputs, per-connection/directional accounting, and exact captured-order baseline byte comparisons. The legacy baseline has 16 Chromium client Initial records (10 decrypted, 6 failed) and 20 curl records (10 decrypted, 10 failed); these are five switched-DCID alias buckets per trace, involving 6 Chromium and 10 curl packet records. Stateful baseline accounting decrypts all 16/20 client Initial packets with zero failures, and TShark byte multisets match 5/5 per trace. The stateful reverse/shuffle cases, however, match 0/5 and 4/5 per trace, respectively; the result is order-sensitive and must not be described as invariant across the whole matrix. QUIC remains the primary engineering investigation; L3 is secondary. Neither result alone establishes novelty, course-rubric completion, or team approval.

Do not describe the standards-defined QUIC Initial key derivation, classic-PCAP reading, or the clean-trace match as the original contribution. First establish a reproducible gap under a measured capture condition and show an improvement over a declared baseline.

## Active primary investigation: stateful Initial context and CID association

The stateful path is a targeted response to the user-observed later-client-Initial decrypt failures, not a claim that an established QUIC implementation lacks CID handling. The association is intentionally scoped to a single direction-normalized UDP 4-tuple. It stores the first client Initial DCID as the original key context, learns client SCIDs and server Initial SCIDs, accepts switched client DCIDs only when they match a learned server SCID, and keeps client/server packet-number reconstruction state separate. Unknown CIDs do not overwrite context. Retry transitions and tuple migration are excluded and must be called out as limitations.

The reported aggregate before/after result is:

| Trace | Client Initial records | Legacy client decrypt success / failure | Distinct switched-DCID aliases / client packets using aliases | Stateful client decrypt success / failure | Complete ClientHellos, legacy / stateful |
|---|---:|---:|---:|---:|---:|
| curl | 20 | 10 / 10 | 5 / 10 | 20 / 0 | 5 / 5 |
| Chromium | 16 | 10 / 6 | 5 / 6 | 16 / 0 | 5 / 5 |

This supports the intended packet-accounting improvement in the captured-order traces: +10 successful curl Initial decrypts and +6 for Chromium, while the complete-ClientHello baseline remains 5/5 per trace and exactly byte-matches TShark 4.6.4. The batch also preserves server-direction totals, context misses, per-connection rows, and hashes. Keep alias **bucket counts** separate from packet records using those aliases.

Implementation lives in `code/quic/src/initial_context.cpp` and `main.cpp`; the C++ tests cover first-DCID retention, a server-SCID alias, duplicate switched packets, unknown-CID rejection, and tuple separation. The batch ran the updated `code/scripts/quic_impairment.py --stateful-initial-context` and `verify_submission_batch.sh`; the raw logs and result JSON are now present in the committed directory. This is user-run evidence inspected from artifacts, not independent Arena reproduction. The reverse/shuffle outcomes reveal order sensitivity and qualify “no regression” to captured-order baselines. The evidence supports a bounded engineering fix, not novelty. Check the QUIC specifications and prior art, course rubric, and team decision before promoting it to an original contribution. Preserve ODCID semantics under RFC 9001 §5.2 and treat Retry / migration as unsupported.

## Previous broad QUIC research question (recovery/diagnostics hypothesis rejected)

> Under controlled packet-capture degradation, how do QUIC v1 ClientHello recovery tools differ in exact-byte recall and in distinguishing incomplete evidence from unsupported or undecryptable traffic?

The evaluated direction was a **capture-quality-aware QUIC Initial recovery and completeness-diagnostics pipeline**. Recovery is rejected for the tested regimes; only a measured diagnostic classification gap could reopen that narrow question. Do not interpret this as the active contribution direction.

## Baseline now available

- `quic_chromium.pcap`: five extracted ClientHellos, lengths 1884, 1891, 1885, 1891, and 1880 bytes.
- `quic_curl.pcap`: five extracted ClientHellos, each 1509 bytes.
- The 5 November stateful batch records exact byte-multiset equality against TShark 4.6.4 for the captured-order baseline: 5/5 ClientHellos per trace, zero misses/extras. The separate earlier `tls.handshake_raw` export/script is not retained; the current batch uses per-case TShark `jsonraw` output and stores the compared byte SHA-256 multisets in its result JSON.
- The committed batch records TShark 4.6.4, GCC 15.2.0, OpenSSL 3.5.5, exact per-case commands, TShark `jsonraw` exports, C++ logs, variants, and hashes. These artifacts were inspected in this checkout, but the WSL execution was not independently regenerated in Arena. The earlier standalone clean `tls.handshake_raw` export/script is not preserved separately.
- The legacy CLI reports ten per-DCID Initial buckets per trace. The retained logs show Chromium's five original-DCID buckets decrypting 10 records successfully and five switched-DCID buckets failing on 6 records; curl's five original buckets decrypt 10 successfully and five switched buckets fail on 10 records. Those switched records are all client-to-server and are not server-direction attempts. Complete extraction remains 5/5 per trace. See `docs/quic/implementation-status.md`, `results/track2/quic-initial-dcid-inventory.json`, and the baseline extractor logs under `results/track2/verification-batch-20261105-054047/`.

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

The committed batch result JSON reports zero misses and extras in every mutated-reference comparison. The 2/2 result in the every-third-drop case is **conditional recall against TShark's output from the same mutated capture**, not five-of-five recovery against the original clean trace. These results establish no extraction gap against TShark for this limited deterministic matrix. They do not establish broad QUIC robustness or independently prove either tool's correctness. The case manifests, variant PCAPs, TShark raw exports, logs, and `impairment-results.json` are now retained under `results/track2/verification-batch-20261104-201936/`; the WSL execution has not been independently rerun in Arena.

### User-reported damaged-flow diagnostic audit (commit `682051e`; baseline correlation reported 5 November 2026)

The user reports `make build` and `make test` passed in Ubuntu WSL (CTest 1/1, pytest 27/27) and mapped the every-third-drop frame selections to the C++ per-DCID output. The selected original frame numbers were curl `[3,31,60,65,94,120]` and Chromium `[3,29,56,59,85,113]`. For each trace, two original ClientHellos remained complete and three were explicitly labeled `client_hello=incomplete`; all three had decrypted CRYPTO data and no decrypt/frame/reassembly errors. The reported missing ranges were:

- **curl:** two flows declared 1509 expected bytes and reported `[1158,1509)`; the third reported `expected_bytes=unknown`, observed extent 1509, and `[0,1158)` within that extent. In the 5 November follow-up, the user maps this DCID to the 1509-byte clean-baseline ClientHello; no suffix is missing.
- **Chromium:** two flows declared 1884/1891 expected bytes and reported `[56,1000)` and `[70,1018)`; the third reported `expected_bytes=unknown`, observed extent 1026, and `[0,78)` within that extent. In the 5 November follow-up, the user maps this DCID to the 1891-byte clean-baseline ClientHello, so the baseline comparison additionally identifies missing suffix `[1026,1891)` that the damaged capture alone cannot infer.

The `observed_extent_only` scope is correct: for the unknown-length flows, the extractor reports only gaps detectable from that damaged capture and does not invent a total handshake length. The baseline-assisted Chromium suffix is an external comparison result, not a falsely claimed C++ observation. The user-reported audit therefore finds no material diagnostic classification gap in these cases. Frame lists and raw logs remain user-reported and are not retained here.

The same run exposed an evaluation-pipeline issue: in this TShark `-T jsonraw` output, repeated `tls.handshake_raw` members can appear at the same object level. Python's default `json.loads()` keeps only the last value for a duplicate object key, so the initial harness could silently lose earlier ClientHellos (the baseline reference count became zero). Commit `fec3b11` scans the raw export text to preserve all matching values. This is a **tooling/data-ingestion finding**, not evidence of a QUIC extractor limitation or an original protocol contribution. The wording should be scoped to this observed TShark JSON output, not generalized to every JSON parser or dissector. The committed verification batch reports the current 39-test Python suite passed in the user's WSL environment.

### Decision and next gate

Do **not** revive the broad recovery/completeness-diagnostics hypothesis: it showed no material gap under the measured stateless matrix. The 5 November batch now archives the WSL CMake/CTest/pytest run, stateful Chromium/curl per-direction and per-connection counters, and exact captured-order baseline byte multisets against TShark 4.6.4. It also shows stateful reverse/shuffle misses, which must be reported as a limitation. The WSL evidence is inspectable but not independently reproduced in Arena. Next gates are targeted prior-art review, explicit course-rubric review, and team approval; do not treat the summary or implementation result as novelty proof.

L3 is a **secondary limitation investigation**, not the primary candidate. The new three-pair evidence is timing-correlated but does not identify an intermediate termination/rewrite mechanism or prove a JA4T attribution error. Continue only with that scoped limitation; see `docs/l3-contribution-plan.md`. Do not describe an MSS outlier alone as proof of a proxy or fingerprint corruption.

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

The damaged-flow diagnostic question remains closed unless a reproducible material misclassification appears. The separately reopened association/accounting hypothesis passes its next gate only if WSL results show lower client Initial decrypt failures on the same packets, no loss or change in complete ClientHello byte sets against TShark 4.6.4, and clearly scoped limitations for Retry/migration. This is an engineering result, not automatically a novelty claim; check prior art, the course rubric, and the team decision before promotion.

## Scaffolded implementation and commands

`code/scripts/quic_impairment.py` provides a deterministic mutation/evaluation harness. It leaves source PCAPs untouched, uses TShark fields to locate Initial CRYPTO-carrying records, records input/variant hashes and exact tool argv, and compares complete ClientHello byte-string multisets from the C++ CLI and TShark on each variant. The default is legacy DCID-keyed mode; `--stateful-initial-context` opts into the new association mode and captures directional/per-connection packet accounting alongside byte comparison. Each run generates clean, reversed, seeded-shuffle, drop-one, drop-every-third, and truncated variants. Logs and raw TShark JSON are written under the work directory.

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

Each run writes `cases.json`, per-case extractor/TShark logs, and `impairment-results.json` with exact-byte recall, missed/extra outputs, incomplete flows, per-direction/per-connection accounting when stateful mode is enabled, and tool return codes. It exits nonzero on a tool/comparison error. Inspect selected frame numbers in `cases.json`; verify mutation semantics before interpreting results. Keep raw artifacts under `results/reproduced/` unless reviewed and deliberately curated.

Run the stateful matrix in separate work directories, adding `--stateful-initial-context` to each command:

```sh
python3 code/scripts/quic_impairment.py \
  --input captures/pcaps/quic_chromium.pcap \
  --work-dir results/reproduced/quic_stateful/chromium \
  --extractor build/code/quic/src/quic-fingerprint --tshark tshark --seed 331 \
  --stateful-initial-context

python3 code/scripts/quic_impairment.py \
  --input captures/pcaps/quic_curl.pcap \
  --work-dir results/reproduced/quic_stateful/curl \
  --extractor build/code/quic/src/quic-fingerprint --tshark tshark --seed 331 \
  --stateful-initial-context
```

1. Run CMake/CTest and the existing Python tests, including the new association/accounting tests.
2. Compare legacy and stateful clean-capture and impairment runs on identical bytes. Review per-connection before/after decrypt counters and keep alias-bucket and switched-packet totals separate.
3. Require unchanged byte-identical complete ClientHello multisets against TShark 4.6.4 for the clean traces; investigate any recall or byte differences rather than assuming.
4. Publish failures and unsupported cases as well as successes, then conduct prior-art/rubric review before making any contribution claim.

## Alternatives not selected at this stage

- L1 reference-tool coverage is not supported by the current clean-trace results.
- L5's reported released-versus-unreleased JA4 difference is not a clean contribution candidate until the missing `ja4-main` raw results and source/build provenance are reproducible; the reported issue is already fixed upstream.
- L3 capture-vantage/JA4T attribution is a secondary limitation investigation. Three timing-correlated container/Wi-Fi pairs exist, but no proxy identity, JA4T impact, or intermediate mechanism is proven; see `docs/l3-contribution-plan.md`.
- L2, L6, and the L7 DoH arm still have missing or incomplete evidence.
