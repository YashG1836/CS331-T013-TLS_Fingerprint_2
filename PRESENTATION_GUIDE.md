# Presentation guide: Track 1 evidence and Track 2 next step

For each observation, state the question, changed condition, supplied output, provenance, and what it does **not** prove. Track 1 results below are imported teammate outputs; consult [`docs/track1-evidence-audit.md`](docs/track1-evidence-audit.md) before presenting them. Do not describe an imported result as independently reproduced in this checkout.

## Before the presentation

- [ ] Run `make test`, `make check`, and `make eval` for the current repository.
- [ ] If Docker and reference tools are available, run `make lab-image` and `make lab-eval`. Fresh outputs go to `results/reproduced/`.
- [ ] Open `PHASES.md`, `captures/manifest.json`, `results/summary.md`, `LEDGER.md`, and `docs/track1-evidence-audit.md`.
- [ ] Use `VIVA_QUESTIONS.md` to prepare; explain evidence limits in your own words.
- [ ] Assign presentation sections within the team; this guide does not assign roles or names.

## 1. Research direction and core

**Show:** `README.md` and `PHASES.md`.

Explain that Track 1 uses deployed reference tools and controlled captures; Track 2 preserves the modular C++ QUIC path: packet parsing, Initial crypto, frame parsing, CRYPTO reassembly, and ClientHello parsing. The current CLI accepts hex datagrams and classic Ethernet PCAP; on the imported Chromium and curl captures it recovered five ClientHellos each. The user reports a TShark 4.6.4 `tls.handshake_raw` byte-set match for all ten. Attribute this to the WSL run and note the raw exports/script are not yet retained in the repo. The clean-capture L1 gap is not supported; the flow model remains limited.

## 2. What is visible in a ClientHello?

**Show:** a ClientHello in Wireshark or the QUIC RFC discussion.

Do not say all ClientHellos are simply plaintext. Ordinary TLS-over-TCP ClientHello fields are normally visible unless ECH is used. In QUIC v1, the ClientHello is in protected Initial packets, but Initial keys are derivable from public protocol inputs; Handshake packet protection is a separate boundary.

## 3. How Track 1 was recorded

**Show:** `captures/manifest.json`, one capture's metadata, and `docs/tests/README.md`.

The teammate snapshot contains 15 PCAP attempts and matching raw tool-output JSON. Fourteen files contain packets; `tls_ipv6.pcap` is empty. TShark and FoxIO share a packet-dissector dependency. The `results/summary.*` files are audited imports, and the unmodified source summary is under `results/imported/`.

## 4. Reproducing the reference-tool analysis

With Docker available, run:

```sh
make lab-image
make lab-eval
cat results/reproduced/summary.md
```

This re-runs TShark/FoxIO on the registered Track 1 captures and writes fresh outputs under an ignored directory. It does not modify imported summaries. It requires the pinned lab image and reference executables; the current integration environment does not have Docker/TShark/JA4, so this rerun is delegated to the team lab.

## 5. Report observations with caveats

- **T1 / QUIC:** the imported summary reports 5/5 ClientHellos for Chromium and curl, and as many as 21 Chromium CRYPTO fragments. It does not validate our C++ extractor.
- **T2 / keys:** the summary reports 0 JA4X/JA4H without keys and 5 with keys. The key log is not committed, so the keyed arm cannot be regenerated from this checkout.
- **T3 / capture point:** the aggregate output reports `pieces_max` 1 vs 2. The narrative's 1586-byte and `1514 + 138` frame values differ from the saved aggregate metrics, and the SYN/MSS data is not preserved in the raw JSON. Do not claim a final proxy result without a targeted rerun.
- **T4 / key share:** the imported output reports a 508-to-1511-byte ClientHello difference and selected groups 29 vs 4588; JA4 changes with the extensions. One client/environment does not establish general behavior.
- **T5 / repeat stability:** the imported output reports 50 distinct JA3s and 15 released-tool JA4s in 50 Chromium ClientHellos, versus 1 JA4 from a specific unreleased FoxIO commit. Root cause and exact tool-source behavior need reproduction; this is not a novel contribution.
- **T6 / IPv6:** no packets were recorded; no comparison was made.
- **T7 / ECH and DNS:** saved page outputs report `sni=plaintext` with ECH off and `sni=encrypted` with ECH on. The ECH+DoH page output is empty, so that arm is incomplete.

## 6. Tool versions and test evidence

The WSL baseline snapshot and Yash's Docker lab use different tool versions; do not combine them as one pin. `results/checkpoint_build_test.txt` is the teammate's captured log, not a run tied to a recorded commit SHA. Current-branch test results should come from `make test` and current CI.

## 7. Next work and contribution candidate

The current modular C++ core is connected to `quic_chromium.pcap` and `quic_curl.pcap`; the user reports exact byte-set agreement with TShark `tls.handshake_raw` on clean captures and the tested reorder/loss/truncation variants. QUIC recovery is not the original-contribution candidate for these conditions; the user-reported WSL audit shows three incomplete statuses per trace with missing-range output. Baseline correlation found no suffix gap for curl and a Chromium suffix beyond the observed extent; the extractor correctly marks that length as unknown. L3 proxy-aware capture-vantage attribution for JA4T/JA4TS is the primary candidate to investigate, not a finding: user-reported checker results on the separate offload captures show repeatable SYN option asymmetry but do not pair the runs. The next step is a controlled simultaneous capture at documented container/bridge/outer points, with the T3 discrepancy resolved and TSO/GSO tested separately. Check prior art and course expectations before any novelty claim.

## 8. If something fails

| Problem | Safe response |
|---|---|
| Docker or reference tools unavailable | Present the audited imported summary, clearly labelled as teammate-supplied, and explain the local command needed to rerun. |
| No network | Do not run `make lab-capture`; `make lab-eval` only needs the committed PCAPs and tools. |
| Need a new capture | Use `make lab-capture CAPTURE_ID=<id>` only with consent. It writes to ignored `captures/reproduced/`; review/hash/count the result and register it separately before analysis. |
| Key-log experiment | Keep session secrets local and ignored. Do not commit keys. |

## Do not claim

- That QUIC ClientHellos are unrecoverable because Initial packets are protected.
- That the current C++ extractor covers all Track 1 traffic or is a complete QUIC flow tracker; only the two QUIC client PCAPs have this reported byte-match check.
- IPv6 results, a successful ECH+DoH run, or T3 proxy findings beyond the retained evidence.
- That FoxIO/TShark are independent packet decoders.
- That the already-reported T5 upstream fix is our original contribution.
