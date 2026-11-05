# Phase 1 vs Phase 2

## Phase 1: what the team reported

- Implemented JA3/JA3S/JA4-style fingerprinting and a detector in Python.
- Tested through a local relay with a small capture set.
- The team later identified weaknesses in evidence coverage, tool choice, and explanation of protocol fields; see the original course report for the authoritative details.

## Phase 2: agreed direction

1. Use deployed reference tools such as FoxIO JA4+ and Wireshark/TShark instead of treating a second fingerprint implementation as the research contribution.
2. Measure seven evidence-backed conditions, with a QUIC v1 depth dive.
3. Select an improvement only after confirming a reproducible gap and checking prior art.
4. Regenerate every reported number from reviewed evidence and commands; retain genuine AI-use records as required by the course.
5. Combine Track 1 (lab, captures, reference-tool measurements) with Track 2 (modular C++ QUIC core).

## Track 1 snapshot imported 3 November 2026

Yash's repository snapshot at commit `b1ffd7c65ae47af1b62184549262ef838c4a234d` supplied 15 PCAP files and T0–T7 explanations. Fourteen PCAPs contain packet records; the IPv6 file is empty. The summary/raw outputs and tool versions are preserved as supplied, with an audited root summary that marks the empty IPv6 comparison as not applicable. The full Track 1 analysis has not been rerun; separately, the user reports a TShark raw-byte check on the two QUIC PCAPs. See [`docs/track1-evidence-audit.md`](docs/track1-evidence-audit.md) and [`results/verification-status.md`](results/verification-status.md).

| Test | Imported observation | Current evidence status |
|---|---|---|
| T1 QUIC | Imported reference outputs report 5/5 ClientHellos for Chromium and curl; Chromium has up to 21 CRYPTO fragments. The committed 5 Nov stateful WSL batch records exact baseline 5/5 ClientHello byte-multiset matches per trace against TShark 4.6.4. | Inspectable user-run WSL evidence, not independent Arena reproduction. Stateful reverse-order and shuffle cases match 0/5 and 4/5 per trace; only captured-order baseline preservation is supported. Separate prior `tls.handshake_raw` export/script remains absent. |
| T2 keys | Summary reports JA4X/JA4H count 0 without keys and 5 with keys. | Key log intentionally absent; keyed output cannot be regenerated. |
| T3 capture point | Summary reports `pieces_max` 1 vs 2 with TSO/GSO changed; narrative also reports large frames and proxy MSS. | Docker vantage; narrative frame values disagree with aggregate summary; targeted rerun needed. |
| T4 post-quantum | Summary reports ClientHello lengths 508 vs 1511 bytes and selected groups 29 vs 4588; JA4 differs. | Team-supplied, one client/environment; no claim that JA4 directly encodes the group. |
| T5 repeat connections | 50 Chromium hellos: 50 JA3s, 15 released-tool JA4s, 1 from a specified unreleased FoxIO commit. | Promising release-vs-unreleased observation; root cause and prior art need verification. |
| T6 IPv6 | PCAP header only, zero packet records. | Not measured. |
| T7 ECH/DNS | Saved page outputs report plaintext SNI with ECH off and encrypted SNI with ECH on. | Imported outputs; DoH page did not load and its arm is incomplete. |

The Docker snapshot reports TShark 4.4.19 and a JA4 tag `v0.18.6` whose executable reports `0.18.5`; the separate Track 2 WSL snapshot reported TShark 4.6.4 and JA4 `0.18.6`. They are distinct environments, not a single reproducible pin. FoxIO's CLI uses TShark; agreement between their outputs is not independent packet-decoder agreement.

The supplied C++ checkpoint log records one CTest target and sanitizer target passing plus nine pytest tests. It does not identify an exact source SHA. The repository's modular C++ architecture, lightweight harness, pytest, CI, and Track 2 runner remain authoritative for current-branch validation.

## Still to do

- Reproduce imported Track 1 analysis in the Docker lab using `make lab-image` and `make lab-eval` if time permits; outputs go under ignored `results/reproduced/` so imported evidence stays immutable.
- Repeat public IPv6 L6 only on a network with working global IPv6. The current artifact is empty and the optional WSL loopback capture attempt failed; neither is a public-egress measurement.
- The 5 November stateful QUIC batch now preserves per-case TShark `jsonraw`, exact baseline byte multisets, directional/per-connection counts, commands, environment, and tests. Its order-mutated cases reveal statefulness limits; include these in any final report. The separate earlier `tls.handshake_raw` export/script remains absent. See [`docs/track2-integration-plan.md`](docs/track2-integration-plan.md) and [`report/report.md`](docs/report/report.md).
- Complete targeted prior-art and course-rubric review before selecting a contribution. The imported T5 upstream fix remains unsuitable as a new code contribution.
- Keep TLS key logs local and ignored; do not commit secrets.
- Write team decisions and contribution records as the team, not retroactively or by inference.
