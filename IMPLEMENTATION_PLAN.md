# CN Project 2 — Implementation Plan

**Team:** T013  
**Plan status:** execution baseline; update decisions only with team agreement and recorded evidence.  
**Schedule basis:** the 15-workday schedule supplied by the team runs 26 October–12 November 2026, with 13 November as a buffer. As of 2 November 2026, the schedule reaches Day 7. A date in the schedule is not evidence that its task was completed; record completion and evidence separately.

This plan turns the approved proposal and working plan into an engineering sequence. The central objective is to investigate practical TLS-fingerprinting problems in real network conditions, support claims with reproducible captures, and then develop and evaluate an original project contribution addressing at least one confirmed problem. The custom QUIC v1 extractor is a candidate research instrument and depth dive—not, by itself, a novel solution. Existing tools remain comparison targets; their capabilities and shared dependencies must be verified rather than assumed.

## 1. Research outcomes

The project has four connected deliverables:

### A. Fingerprinting landscape

Document JA3, JA3S, JA4, JA4S, JA4T, JA4X, and JA4H. For each, record:

- Input fields and protocol layer.
- RFC and section that define each protocol field.
- Construction, ordering, sorting, GREASE rules, exclusions, and output form.
- What a value can suggest and what it cannot establish.
- Visibility to an observer with and without TLS secrets.
- Maintainer, implementation, version, and date checked.

**Target files:** `docs/landscape.md` and individual tables under `docs/basics/`. The current shared introductory reading is `docs/reading-guide.md`.

### B. Seven evidence-backed limitations

Investigate the seven limitation hypotheses in §6, subject to the approved project scope. Each row needs a real committed capture, a reproducible command, exact tool/configuration metadata, an observed result, and a protocol-level explanation with RFC section citations. Predictions stay labelled as hypotheses until the evidence is collected. If a limitation is removed, replaced, or combined, record the reason and obtain the required instructor/team approval rather than silently changing the approved count.

**Target file:** `LEDGER.md`, linked to capture records in `corpus/manifest.json` and generated evaluation outputs. Simulations must be explicitly labelled and must not be presented as observed deployments.

### C. Two depth dives and a solution

1. **QUIC investigation:** establish what pinned existing tools can and cannot recover from QUIC captures; implement/test the v1 Initial extraction path; validate recovered bytes independently; then evaluate any observed tool or capture-condition gap.
2. **Passive visibility:** measure what JA4S/JA4X add when the necessary plaintext is available, and classify what a passive tap can observe without secrets.
3. **Original solution selection:** after the limitation evidence and baselines are reviewed, select at least one confirmed problem with an unresolved practical aspect. Develop a project-original technical contribution and compare it against the relevant existing approach on the same evidence. Do not declare the QUIC extractor itself novel merely because it is custom C++ or implements RFC-defined Initial decryption.

The contribution should be original to this project and supported by a state-of-the-art/tool check; do not claim that no one has ever solved the problem unless that broader claim has actually been established.

### D. Reproducible evaluation

A clean checkout should build the C++ component, run C++ and Python tests, validate the manifest, run the declared analyses, and regenerate any printed values from committed evidence. The report is not the source of measured numbers.

### Two-phase research logic

**Phase 1 — investigate first:** establish the baseline with pinned tools; identify where a limitation occurs; determine whether its cause is protocol behaviour, implementation/tool coverage, or capture/network conditions; and quantify its effect on extraction, fingerprint values, stability, visibility, or attribution. The finding must come from measured evidence, not from the hypothesis alone.

**Phase 2 — contribute and evaluate:** choose a confirmed gap after Phase 1, explain why existing approaches are insufficient for that case, implement a project-original response, and evaluate it against the baseline on the same captures. Reimplementing an RFC mechanism may be necessary infrastructure, but it is not sufficient by itself to claim a research contribution.

QUIC remains the required investigation/depth-dive focus from the project brief. The specific original solution should still be chosen from the measured gaps; if the solution is a QUIC improvement, its contribution must be demonstrated beyond basic RFC-compliant Initial decryption.

## 2. Language and tool decisions

| Component | Choice | Boundary / reason |
|---|---|---|
| QUIC packet parsing | C++20 | Explicit bounded binary parsing and packet-buffer handling. This is a systems-design choice, not a claim that C++ is inherently faster or more correct than Python. |
| QUIC Initial cryptography | C++20 + OpenSSL 3.x | Use library HKDF, AES header-protection, and AEAD APIs. Do not implement cryptographic primitives. |
| Frame parsing and CRYPTO reassembly | C++20 | Parse offsets and assemble handshake bytes with explicit bounds, overlap checks, and allocation limits. |
| TLS ClientHello extraction | C++20 | Validate handshake framing and nested lengths before extracting fields. |
| JA4 construction | Verified reference implementation initially | Do not create a second JA4 implementation simply for convenience. Validate all QUIC-specific encoding and field construction against the published specification and an independent reference before emitting a result. |
| Reference tools | FoxIO JA4+ and Wireshark/tshark | Treat as independent black boxes; compare identical bytes and record exact versions/commands. |
| Capture | tcpdump/dumpcap as available | Prefer real traffic. Record vantage point, interface, direction, offload settings, MTU, NAT/proxy conditions, and capture start/stop. |
| Orchestration/evaluation | Python 3.12 | Validate manifests, run tools, collect outputs, calculate statistics, and generate tables. Python does not replace the C++ QUIC processing core. |
| Build | CMake | Reproducible C++ build with OpenSSL 3.x. |
| Tests | GoogleTest for C++; pytest for Python | Test modules independently and test the corpus/evaluation workflow. The current checkpoint has a dependency-light C++ test executable rather than GoogleTest; migrate it or record an explicit team-approved reason before calling this requirement satisfied. |
| CI | GitHub Actions | Build and test from a clean checkout; record dependency versions. |
| Corpus metadata | JSON manifest | Connect each capture to its conditions, tool versions, commands, expected properties, and report reference. |

### Why a hybrid design

QUIC packet processing requires careful handling of protected binary headers, cryptographic keys, frames, offsets, and reassembled handshake bytes. C++ supplies explicit control over those data paths. OpenSSL supplies the cryptographic primitives. Python is more suitable for experiment orchestration and statistics, where a C++ rewrite would add work without improving the research question. Neither language choice substitutes for independent validation.

## 3. Repository target layout

Add components when they are implemented; do not create empty files for appearance alone.

```text
README.md
IMPLEMENTATION_PLAN.md
Makefile
CMakeLists.txt
pyproject.toml
requirements.txt
DECISIONS.md                 # written/reviewed in the team's own words
WHO_KNOWS_WHAT.md
LEDGER.md
src/quic_fingerprint/
  CMakeLists.txt
  include/quic/{packet_parser,initial_crypto,frame_parser,crypto_reassembly}.hpp
  include/tls/client_hello.hpp
  packet_parser.cpp
  initial_crypto.cpp
  frame_parser.cpp
  crypto_reassembly.cpp
  client_hello.cpp
  main.cpp
experiments/
  run_baseline.py
  run_scenarios.py
  compare_fingerprints.py
  evaluate.py
corpus/
  manifest.json
  pcaps/{baseline,quic,ipv6,vantage}/
  metadata/
tests/
  cpp/
  python/
docs/
  landscape.md
  capture-method.md
  baseline-agreement.md
  basics/
  limitations/
  quic/
  passive-visibility.md
  report.md
ai/README.md
.github/workflows/ci.yml
```

The original Project 1 implementation should not be forked as the base for this work. Reuse a specific, independently verified algorithm only where that is justified; rebuild the capture, flow, evidence, and evaluation model around Project 2.

## 4. QUIC v1 implementation stages

Implement and test each stage before integrating the next. The first scope is QUIC v1 client Initial extraction. Do not claim support for v2, Retry, 0-RTT, migration, or all frame types until each is separately implemented and tested.

### Stage 1 — Long-header and datagram parsing

Parse the v1 long header and the fields needed for Initial packet processing: version, packet type, destination/source connection IDs, Initial token length/token, protected length, packet boundary, and packet-number offset.

Requirements:
- Use `std::span<const std::uint8_t>` or another bounded view.
- Check bounds before every read and before offset-plus-length arithmetic.
- Decode variable-length integers per RFC 9000 §16.
- Respect packet lengths and allow coalesced long-header packets in one UDP datagram.
- Reject truncated, malformed, and unsupported-version inputs clearly.
- Do not assume one datagram equals one QUIC packet.

**Tests:** v1 long headers, valid Initial, truncations at each field, invalid CID length, truncated variable integers, inconsistent packet lengths, and multiple coalesced packets.  
**Gate:** extract the supported header fields from a known v1 datagram and reject malformed inputs without out-of-bounds reads.

### Stage 2 — Initial key derivation

Implement RFC 9001 §5.2 and the relevant TLS 1.3 HKDF-Expand-Label procedure. Derive Initial, client/server Initial, packet key, IV, and header-protection key from the protocol version and original destination connection ID. Do not hard-code a connection ID or key set.

**Tests:** RFC-published derivation vector; multiple connection IDs; client and server secret derivations; invalid lengths; output comparison with an independent implementation.  
**Gate:** exact derivation vector match.

### Stage 3 — Header protection and AEAD decryption

Follow the order in RFC 9001: locate the header-protection sample; remove header protection; recover the truncated packet number; reconstruct the full packet number; form the unprotected header as associated data; authenticate and decrypt the protected payload. Reject invalid tags and insufficient samples.

**Tests:** valid Initial packets in both directions; tampered ciphertext; truncated tags; packet-number reconstruction; invalid sample bounds.  
**Gate:** decrypt a known Initial packet and compare the plaintext with an independent result.

### Stage 4 — Initial frame parsing

Initially parse only the frame types needed to reach CRYPTO data and safely skip supported control frames in Initial packets. For each CRYPTO frame, extract offset, length, and data. Reject unsupported frame types rather than guessing their layout.

**Tests:** CRYPTO at offset zero/nonzero; multiple CRYPTO frames; PADDING, PING, ACK/ACK_ECN; truncated frame data; invalid lengths/offsets; unsupported frames.  
**Gate:** recover CRYPTO boundaries and offsets correctly.

### Stage 5 — CRYPTO reassembly

Reassemble by protocol offset, not packet arrival order. Accept out-of-order fragments and equal duplicate overlap; detect conflicting overlap, missing ranges, and incomplete handshakes. Bound retained data and reject arithmetic overflow or unreasonable offsets. Do not return a fingerprint for incomplete data.

**Tests:** one-frame ClientHello; two or more fragments; reverse arrival; equal duplicates; conflicting overlap; missing bytes; excessive declared length.  
**Gate:** recover the same complete handshake bytes from a multi-packet capture and reject incomplete/malformed input.

### Stage 6 — ClientHello and fingerprint integration

Parse the complete TLS handshake framing, then validate ClientHello fields and nested vectors. Separate fields required for structural validation from fields used by the chosen JA4 specification. Validate GREASE, sorting, exclusions, ALPN and the QUIC protocol marker against the current FoxIO specification/reference implementation. Do not merely change the TCP protocol character and assume the result is correct.

**Gate:** compare the recovered ClientHello byte-for-byte with an independent decoder and compare fingerprint fields—not only the final hash—with a verified reference.

### Stage 7 — Client matrix and failure taxonomy

Test at least four distinct QUIC clients and target at least ten connections per client where practical. For every connection record client/version, QUIC version, capture conditions, Initial recovery, decrypt success, ClientHello completeness, fingerprint result, and failure reason.

Report only failures actually tested or observed. Potential categories include unsupported version, incomplete capture, missing Initial, invalid reassembly, or unsupported packet-processing condition. Do not claim Retry, migration, or 0-RTT support from a basic Initial success.

## 5. Seven limitation experiments

| ID | Question / hypothesis | Required evidence |
|---|---|---|
| L1 — QUIC tool coverage | QUIC Initial protection is not, by itself, a passive-observer confidentiality barrier: v1 Initial secrets are derivable from public protocol inputs. Which pinned tools actually extract and fingerprint the ClientHello, and where is a measured gap? | QUIC capture; pinned tool outputs on identical bytes; recovered ClientHello; byte-level comparison; exact reproduction command and tested failure cases. Treat unsupported behavior as a tool limitation only after reproducing it. |
| L2 — Passive JA4X/JA4H visibility | What changes when the same analysis has TLS secrets versus no secrets? | Matched traffic/capture metadata, with-key and without-key outputs, tool versions, and explanation of which layer is encrypted. |
| L3 — Capture vantage point | Which TCP/network values belong to the endpoint, relay, or proxy? | Matched client/relay/proxy captures; SYN evidence; interface, NAT, offload, MTU, and path metadata. |
| L4 — Large hybrid key shares | Does the selected client actually offer/negotiate a hybrid group, and which lengths/fingerprint fields change? | Paired captures; group negotiation proof; ClientHello sizes, packet counts, and fingerprint comparisons. |
| L5 — Stability and collisions | How stable are fingerprints over repeated connections, and do applications sharing a TLS stack collide? | Repeated connections per client; two controlled applications where feasible; generated distinct-hash/collision statistics. |
| L6 — IPv4 versus IPv6 | Does the TLS fingerprint stay the same while transport or attribution changes? | Matched same-client IPv4/IPv6 captures; generated fingerprints; address/capture conditions; separate layer-specific analysis. |
| L7 — ECH / hostname attribution | What is visible in the outer ClientHello and what attribution context is removed? | Genuine ECH traffic with configuration, or a clearly marked simulation; captured tool output; separate analysis of DNS correlation. |

Encrypted DNS belongs in attribution analysis: it does not automatically change a TLS ClientHello. Certificate abridging is a forward-looking watch item unless a real deployment is captured. Simulations must never be labelled as observed network traffic.

## 6. Python experiment harness

`corpus/manifest.json` is the record connecting evidence to reproducible results. Each capture record should include a stable ID, scenario, capture path, protocol/client/version, capture method and vantage, commands, tool versions, expected properties, and links/IDs for metadata and report sections. Exact generated values belong in machine-generated output, not hand-typed report tables.

The command surface should be:

```sh
make build     # configure and build C++
make test      # C++ tests and pytest suite
make check     # validate manifest, evidence references, and invariants
make eval      # run declared analyses and regenerate report data
make capture   # optional; document privileges/interface/configuration
```

The evaluator should check referenced captures, run declared tools, collect machine-readable output, compare reference/custom results, calculate statistics, and report missing evidence or mismatches. It must also test failure paths: missing capture, missing executable, malformed tool output, duplicate manifest IDs, and inconsistent expected properties. A fresh clone should have one documented reproduction path.

## 7. Team responsibilities and review

| Role | Primary | Secondary / review |
|---|---|---|
| P1 | C++ QUIC packet parsing and Initial decryption | QUIC integration tests; explain supported/unsupported cases. |
| P2 | ClientHello extraction and passive visibility | RFC field documentation; review QUIC parsing and key visibility. |
| P3 | Client matrix, repeated connections, version/library comparison | Fingerprint construction validation; compute stability/collision statistics. |
| P4 | Capture infrastructure, manifest, Python harness, CI | IPv4/IPv6 and vantage experiments; verify clean-clone reproduction. |

The team must assign actual names to P1–P4; this document does not infer them. Each person should make a concrete code or technical-artifact contribution, review at least one component outside their primary responsibility, and be able to explain the overall pipeline. For a human contributor history, use team branches and reviewed PRs as the team setup allows; never invent contributions or author names.

Keep raw, timestamped AI-use records as required by the course, and write `DECISIONS.md` in the team's own words. Neither file should be fabricated or retroactively presented as a contemporaneous record.

## 8. Calendar proposed by the team

This reproduces the supplied 15-workday schedule. Task completion must be recorded from actual evidence; dates below do not claim work has happened.

| Day/date | Owner(s) | Target / gate |
|---|---|---|
| 1 — Mon 26 Oct | All | Confirm scope; record tool versions; begin landscape and human decisions. Gate: each person explains one fingerprint. |
| 2 — Tue 27 Oct | All | Baseline tools on same captures; compare outputs; first manifest entries. Gate: reproduce/explain agreement or disagreement. |
| 3 — Wed 28 Oct | P4 + P1 | Capture setup, initial Python harness, build/test/check commands, CI, capture-method metadata. Gate: clean checkout builds current code. |
| 4 — Thu 29 Oct | P2 + P3 | OS/client comparison; record actual TLS library/version; start field documentation. Gate: explain controlled variable. |
| 5 — Fri 30 Oct | P3 | Old/new versions and repeated connections; generate hash-stability counts. Gate: statistics computed from committed evidence. |
| 6 — Sat 31 Oct | P3 + P4 | Same-library apps and supported hybrid key exchange. Gate: verify actual negotiation before claiming change. |
| 7 — Mon 2 Nov | P1 | QUIC capture and reference-tool baseline before custom parsing. Gate: document what existing tools return on that capture. |
| 8 — Tue 3 Nov | P4 + P1 | IPv4/IPv6 and capture-vantage comparisons; finish first manifest schema. Gate: assign observations to endpoint, proxy, or capture. |
| 9 — Wed 4 Nov | P2 + P4 | Genuine ECH or labelled simulation; encrypted-DNS attribution; certificate-abridging analysis; ledger review. Gate: no simulation represented as deployment. |
| 10 — Thu 5 Nov | All | Mid-project demo and scope decision. Prioritize correct QUIC v1 extraction over optional breadth if time is constrained. |
| 11 — Fri 6 Nov | P1 + P2 review | Long-header parser, Initial key derivation, HP removal, decryption, tests/sanitizers. Gate: known packet result independently verified. |
| 12 — Mon 9 Nov | P1 + P2 | Frame parsing, offset-aware reassembly, full ClientHello, passive-visibility work. Gate: fragmentation tests pass; incomplete handshake rejected. |
| 13 — Tue 10 Nov | P4 + team | Integrate evaluator; run experiment matrix; generate tables; reconcile mismatches. Gate: every printed number regenerates. |
| 14 — Wed 11 Nov | All | Report, RFC citations, clean-clone tests, logs/contribution audit, rehearsal. Gate: another member reproduces core demonstration. |
| 15 — Thu 12 Nov | All | Freeze, final acceptance, release/tag, viva preparation. Friday 13 Nov is buffer. |

**Scheduling note:** on 2 November, Days 1–6 are in the past. Do not mark them complete from the calendar. If their work/evidence is missing, update priorities with the team and use the buffer/scope cut honestly rather than compressing unverified experiments into a false completion claim.

## 9. Acceptance criteria

| Area | Required before claiming completion |
|---|---|
| Packet parser | Supported QUIC v1 headers and packet boundaries parse correctly; malformed input fails safely. |
| Initial cryptography | Derivation vector and full packet decryption match independent evidence; tampered packets fail authentication. |
| Frame parser | Supported frame boundaries and CRYPTO offsets are correct; unsupported frame is rejected explicitly. |
| Reassembly | Out-of-order/equal overlap/conflicting overlap/gap/size-limit cases are tested. |
| TLS parser | Complete valid ClientHello parses; truncation, inconsistent lengths, and malformed vectors fail safely. |
| JA4 integration | QUIC-specific construction matches independent specification/reference fields. |
| Original solution | Addresses a confirmed, practically unresolved gap; compared with a pinned baseline on the same captures using predeclared success metrics, with improvements and regressions reported. |
| Experiment harness | Manifest and failure paths validated; outputs regenerate from corpus. |
| Corpus and ledger | Every reported limitation has committed capture, exact command, metadata, observation, and RFC section. |
| Clean reproduction | Build, tests, check, and evaluation work from a clean clone on a second machine. |
| Team contribution | Actual team assignments and reviews are documented honestly; all can explain the implementation. |

Use AddressSanitizer and UndefinedBehaviorSanitizer where supported. Test malformed/truncated inputs, extreme lengths, missing captures, missing tools, and inconsistent manifest entries intentionally.

## 10. Questions to prepare for the viva

1. Why C++ for this core and Python for the harness? What evidence would justify a performance claim?
2. Why can a passive observer derive QUIC Initial keys, and what does that not let them decrypt?
3. Why remove header protection before AEAD decryption?
4. Why are packet boundaries and TLS handshake-message boundaries different?
5. Why must CRYPTO data be reassembled by offsets, and how are duplicate/conflicting overlaps handled?
6. Why reuse a JA4 reference implementation rather than implement the entire fingerprint family again?
7. What does a fingerprint identify, and why is it not proof of an application or user?
8. What can a tap see when TLS keys are unavailable? Which fingerprints require plaintext or a SYN?
9. What exactly changed in the PQ, IPv6, ECH, or encrypted-DNS scenario, and how did the capture prove it?
10. Can another person regenerate every number in the report from the committed corpus?

## 11. Shortcuts to avoid

- Do not choose C++ merely to make the project look sophisticated, or claim it is inherently faster without measurements.
- Do not rewrite cryptographic primitives.
- Do not assume one UDP datagram contains one QUIC packet.
- Do not concatenate CRYPTO frames in arrival order.
- Do not claim fragmentation support without out-of-order, overlap, gap, and incomplete tests.
- Do not change a JA4 protocol character and call that QUIC support without specification/reference validation.
- Do not claim a PQ group was negotiated without evidence.
- Do not claim ECH, certificate abridging, or other simulated traffic was observed on the network.
- Do not infer that a changed fingerprint proves a different application.
- Do not report a number that cannot be regenerated from a committed capture.
- Do not claim support for Retry, migration, 0-RTT, or QUIC v2 merely because the basic v1 Initial path works.
- Do not leave integration, review, or report generation to one person.

## 12. Checkpoint status and next action

The repository checkpoint currently contains the beginnings of the C++ v1 long-header, Initial-key, frame, reassembly, and ClientHello path plus Python manifest validation. The corpus is empty, so no limitation has an experimental result yet. The full OpenSSL-dependent build/decryption test still needs to be run on a machine with CMake and OpenSSL 3 development headers. The C++ test runner is currently dependency-light rather than GoogleTest; that remains a plan-vs-code gap to resolve explicitly.

**Next action for the team:** first build and test the checkpoint using the commands in `README.md`; then establish the QUIC reference baseline from a real capture using pinned tools before extending the parser. Record test output and tool/capture versions in the repository. Review the measured limitations before selecting the original solution. Do not describe an acceptance gate as passed until the evidence exists, and do not present RFC-defined Initial decryption alone as the novel contribution.
