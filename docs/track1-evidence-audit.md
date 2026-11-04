# Track 1 evidence audit and cross-check

## Source and scope

The Track 1 capture set and reports were imported from Yash's repository snapshot, source commit [`b1ffd7c65ae47af1b62184549262ef838c4a234d`](https://github.com/YashG1836/CS331-T013-TLS_Fingerprint_2/commit/b1ffd7c65ae47af1b62184549262ef838c4a234d). The branch ZIP SHA-256 was `044fe1a27924cb63e13a26708f1a8d402454d49e3fa7ca8547f8fac28f2f603e`. The archive contains 15 `.pcap` files, 15 corresponding raw analysis JSON files, and the supplied summary. All PCAP record framing was checked during import: 14 files contain packets; `tls_ipv6.pcap` is only a 24-byte PCAP global header with zero packet records. Checksums are recorded per capture in `captures/metadata/` and validated by `make check`.

The raw source summaries are preserved unchanged in `results/imported/`; `results/summary.json` and `results/summary.md` are audited derivatives. They correct the source summary's `tools_agree: true` for the empty IPv6 capture to “not comparable” (two empty result sets are not an agreement). `tls_ipv6` is an attempted test, not IPv6 evidence.

## Cross-check against Track 2's earlier baseline and tests

- Track 2's earlier `quic-v1-baseline.pcapng` is a separate aioquic capture to `cloudflare.com`, with SHA-256 `1cd5f8c05b5b966eed1ae339eeec80b86b830deccda81489dabefb28f272ec7a`. Yash's `quic_chromium.pcap` and `quic_curl.pcap` are separate five-repeat client captures to `cloudflare-quic.com`. Different JA4 strings are expected across those different clients/captures; there is no capture-hash or same-scenario contradiction.
- Yash's supplied summary reports 5/5 QUIC ClientHellos from each client, matching JA4 values between TShark and FoxIO for those runs, and up to 21 CRYPTO fragments in Chromium. These are imported, team-reported results, not rerun here. FoxIO's Rust CLI uses TShark, so this is cross-CLI consistency, not two independent packet decoders.
- The reference environments are different and must not be blended into one pin: Track 2's WSL snapshot reports TShark 4.6.4 and a JA4 executable reporting 0.18.6, while Yash's Docker snapshot reports TShark 4.4.19 and a `v0.18.6` JA4 tag whose binary reports 0.18.5. Yash also compared an unreleased FoxIO commit `c6469a7b0dbf8fe963810162429fbfd9d1acc4d5` (`ja4-main`, reports 0.18.6). The exact binary/source relationship for each environment remains a provenance item.
- `results/checkpoint_build_test.txt` is Yash's captured log: 1 CTest target passed, 9 Python tests passed, and 1 sanitizer CTest target passed. T0 separately reports 4 Track 1 script checks. It does not identify the exact Track 2 source SHA, so it is corroboration, not a substitute for the current branch's own tests. The branch preserves the modular core and lightweight harness; the new capture reader and PCAP CLI integration are separately covered by the current branch's CTest and pytest runs, recorded in `results/verification-status.md`.

## Important interpretation and data-quality caveats

- **L1 / QUIC:** the supplied client captures do not show a reference-tool QUIC ClientHello gap. The current C++ extractor recovers five complete ClientHellos from each imported capture. A later user-run WSL batch is committed at `results/track2/verification-batch-20261104-201936/`; its hashes/results were inspected here and it reports 54/54 exact-byte matches to TShark output across two traces and six cases each. The WSL execution was not independently reproduced in Arena, and TShark is the comparator on the same PCAP variant, not independent ground truth. The older standalone `tls.handshake_raw` export/script is not retained separately. The 21-fragment Chromium record remains useful for bounded CRYPTO-reassembly tests, but the clean-trace result does not establish a novel gap.
- **L2 / key logs:** the source summary reports JA4X/JA4H values with a key log, but the key-log file is intentionally not imported. The keyed result cannot be regenerated from the committed artifacts. Do not commit session secrets; recapture a controlled session if this arm must be reproduced.
- **L3 / offload:** the test is inside Docker Desktop, not on the physical wire. Its explanatory T3 page reports a 1586-byte frame and `1514 + 138`-byte split, whereas the imported aggregate summary reports `biggest_frame` 4913/2962 and `pieces_max` 1/2. These are not the same measurement definition; the narrative numbers are not independently represented in the saved raw JSON. Re-run a targeted SYN/segment/frame query before using the proxy/MSS explanation as a final result.
- **L4 / post-quantum:** the summary reports ClientHello lengths 1511 versus 508 bytes and negotiated groups 4588 versus 29. JA4 also differs because the extension set/count differs; do not imply JA4 directly encodes the selected group. This remains a one-client, one-environment observation.
- **L5 / stability:** the imported summary reports 50 Chromium ClientHellos, 50 distinct JA3s, 15 distinct JA4s from the released tool path, and 1 from `ja4-main`; curl/Python each report 1 distinct JA4 in 10 ClientHellos. The committed per-capture raw JSON does not include the `ja4-main` records behind that summary value, so that particular number cannot be recomputed from the raw file set. This is a promising release-versus-unreleased regression observation, not a novel contribution. It needs a reproducible tool build and targeted check of the raw GREASE/signature-algorithm values before claiming the cause or deployment impact.
- **L6 / IPv6:** no packets were captured; no fingerprint comparison is possible.
- **L7 / ECH and DoH:** the supplied page output reports `sni=plaintext` for ECH off and `sni=encrypted` for ECH on. The DoH page output is empty, while the summary includes 12 ClientHello rows from that pcap; those rows may be background connections and do not prove the intended page loaded over ECH+DoH. Treat that arm as incomplete.
- The capture script's log does not record per-client exit codes robustly. Reproduced runs from the imported scripts now record failures explicitly and write to ignored reproduction directories rather than overwriting evidence.

## What was integrated and what was deliberately excluded

All 15 PCAP files, all 15 raw tool-output JSON files, the source summary, tool versions, C++ checkpoint log, capture recipes, test explanations T0–T7, lab Dockerfile, and Track 1 guide documents are integrated. Key logs, the teammate's personal meeting transcript, and AI prompt history were not copied. The small ECH page observations were transcribed with the workstation IP and dynamic network identifiers omitted; this is documented in `results/track1/page-observations.md`.

## Reproduction commands

From the repository root, when Docker is available:

```sh
make lab-image
make lab-eval
```

`make lab-eval` analyses committed PCAPs and writes fresh outputs only under `results/reproduced/`; it does not overwrite the imported baseline. To make a new network capture, explicitly choose one ID and run:

```sh
make lab-capture CAPTURE_ID=tls_ipv6
```

The capture target requires network access and writes under ignored `captures/reproduced/`. It does not update the evidence manifest automatically; review its provenance and packet count before registering it. For a fresh L2 keyed run, keep the key log local and uncommitted.
