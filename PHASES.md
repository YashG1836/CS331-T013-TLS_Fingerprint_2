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

Yash's repository snapshot at commit `b1ffd7c65ae47af1b62184549262ef838c4a234d` supplied 15 PCAP files and T0–T7 explanations. Fourteen PCAPs contain packet records; the IPv6 file is empty. The summary/raw outputs and tool versions are preserved as supplied, with an audited root summary that marks the empty IPv6 comparison as not applicable. They have not been re-run in this checkout. See [`docs/track1-evidence-audit.md`](docs/track1-evidence-audit.md).

| Test | Imported observation | Current evidence status |
|---|---|---|
| T1 QUIC | TShark/FoxIO outputs report 5/5 ClientHellos for Chromium and curl; Chromium has up to 21 CRYPTO fragments. | Team-supplied; shared TShark dissection; not a C++ extractor test. |
| T2 keys | Summary reports JA4X/JA4H count 0 without keys and 5 with keys. | Key log intentionally absent; keyed output cannot be regenerated. |
| T3 capture point | Summary reports `pieces_max` 1 vs 2 with TSO/GSO changed; narrative also reports large frames and proxy MSS. | Docker vantage; narrative frame values disagree with aggregate summary; targeted rerun needed. |
| T4 post-quantum | Summary reports ClientHello lengths 508 vs 1511 bytes and selected groups 29 vs 4588; JA4 differs. | Team-supplied, one client/environment; no claim that JA4 directly encodes the group. |
| T5 repeat connections | 50 Chromium hellos: 50 JA3s, 15 released-tool JA4s, 1 from a specified unreleased FoxIO commit. | Promising release-vs-unreleased observation; root cause and prior art need verification. |
| T6 IPv6 | PCAP header only, zero packet records. | Not measured. |
| T7 ECH/DNS | Saved page outputs report plaintext SNI with ECH off and encrypted SNI with ECH on. | Imported outputs; DoH page did not load and its arm is incomplete. |

The Docker snapshot reports TShark 4.4.19 and a JA4 tag `v0.18.6` whose executable reports `0.18.5`; the separate Track 2 WSL snapshot reported TShark 4.6.4 and JA4 `0.18.6`. They are distinct environments, not a single reproducible pin. FoxIO's CLI uses TShark; agreement between their outputs is not independent packet-decoder agreement.

The supplied C++ checkpoint log records one CTest target and sanitizer target passing plus nine pytest tests. It does not identify an exact source SHA. The repository's modular C++ architecture, lightweight harness, pytest, CI, and Track 2 runner remain authoritative for current-branch validation.

## Still to do

- Reproduce the reference analysis in the Docker lab using `make lab-image` and `make lab-eval`; outputs go under ignored `results/reproduced/` so imported evidence is preserved.
- Reconcile T3 measurements and repeat T6 only on a network with working IPv6.
- Obtain a TShark raw reassembled-ClientHello export and compare exact bytes from both captures; current local extraction confirms counts, total lengths, TLS framing, and parsing but not byte equality. Expand unsupported-case and packet-order tests. See [`docs/track2-integration-plan.md`](docs/track2-integration-plan.md).
- Evaluate the Track 2 QUIC recovery pipeline as a candidate contribution, but verify prior art and the course rubric before claiming novelty. The reported T5 fix already exists upstream in unreleased code.
- Keep TLS key logs local and ignored; do not commit secrets.
- Write team decisions and contribution records as the team, not retroactively or by inference.
