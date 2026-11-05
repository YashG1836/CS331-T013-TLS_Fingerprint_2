# Files guide: Track 1 evidence + Track 2 QUIC core

## Project flow

```text
Track 1 manifest/recipes → lab capture → immutable PCAP evidence
                                  ↓
                        TShark + FoxIO JA4 outputs
                                  ↓
                         imported / reproduced summaries

Track 2 classic-PCAP reader → UDP datagrams → modular QUIC v1 core
                              → Initial decrypt → DCID-scoped CRYPTO reassembly
                              → ClientHello bytes → user-reported exact TShark byte-set match
                              → retain raw exports/script; test impaired-capture behavior
```

## Top level

| File | Purpose |
|---|---|
| `README.md` | Current architecture, scope, and commands. |
| `IMPLEMENTATION_PLAN.md` | Milestones, roles, deadlines, and acceptance gates. |
| `LEDGER.md` | Seven limitation rows, imported evidence status, and contribution candidates. |
| `docs/original-contribution-plan.md` | QUIC recovery candidate disposition and bounded damaged-flow diagnostic audit. |
| `docs/l3-contribution-plan.md` | Secondary L3 capture-vantage limitation investigation, paired evidence, and non-overclaiming gates. |
| `docs/landscape.md` | Preliminary fingerprint-family landscape and open prior-art review matrix. |
| `docs/verification-batch.md` | One-pass WSL verification and evidence collection, with the Windows capture as a coordinated manual step. |
| `DECISIONS.md` | Evidence-based working decisions and human approval gates; not a fabricated team meeting record. |
| `ai/prompts.txt` | Partial, explicitly incomplete verbatim prompt record; not a full timestamped course export. |
| `PHASES.md` | Phase 1 lessons and Track 1/Track 2 state. |
| `GLOSSARY.md` | Plain-language protocol and fingerprint terms, including the QUIC Initial visibility distinction. |
| `VIVA_QUESTIONS.md` | Study guide; imported claims are qualified by current evidence status. |
| `PRESENTATION_GUIDE.md` | Presentation outline with caveats and local reproduction steps. |
| `PROJECT2_PLAN.md`, `PROJECT2_PROPOSAL.md`, `PROJECT1_AUDIT.md` | Existing course planning/audit artifacts. |
| `.github/workflows/ci.yml` | Current repository build, CTest, pytest, and manifest validation. |

## Capture corpus and manifest

| Path | Purpose |
|---|---|
| `captures/manifest.json` | Current schema; registers the existing QUIC v1 baseline plus all 15 Track 1 capture attempts and their recipes, hashes, metadata, and outputs. |
| `captures/pcaps/` | Original pcapng baseline and 15 imported `.pcap` files. The IPv6 file is retained but explicitly marked empty (zero packets). |
| `captures/metadata/` | One JSON metadata record per capture, including source, version, hash, and missing-provenance notes. |
| `captures/config/` | Chromium ECH-off and DoH policies required by the imported recipes. |
| `captures/keylogs/` | Ignored local-only TLS session keys; no teammate key log was imported. |
| `captures/reproduced/` | Ignored outputs from explicit `make lab-capture` runs. |

## Code

| Path | Purpose |
|---|---|
| `code/quic/src/capture_reader.cpp` and `include/quic/capture_reader.hpp` | Classic-PCAP v2.x Ethernet UDP reader for unfragmented IPv4/IPv6; reports unsupported cases explicitly. |
| `code/quic/src/main.cpp` | `--hex` input plus first-stage `--pcap` extraction, diagnostics, and recovered ClientHello hex. |
| `code/quic/src/packet_parser.cpp` | QUIC v1 packet boundaries and variable integers. |
| `code/quic/src/initial_crypto.cpp` | Initial key derivation, header protection, authenticated decryption. |
| `code/quic/src/frame_parser.cpp` | Supported Initial frame parsing. |
| `code/quic/src/crypto_reassembly.cpp` | Offset-aware CRYPTO assembly and conflict/limit checks. |
| `code/quic/src/client_hello.cpp` | Bounds-checked TLS ClientHello parsing. |
| `code/quic/tests/` | Lightweight C++ test harness; no GTest dependency. |
| `code/scripts/evaluate.py` | Hash/metadata/artifact validation and conservative evidence status. |
| `code/scripts/reference_baseline.py` | Existing single-capture reference runner. |
| `code/scripts/analyze.py` | Track 1 multi-capture TShark/FoxIO runner; new outputs go to `results/reproduced/`. |
| `code/scripts/quic_impairment.py` | Deterministic QUIC PCAP reordering/loss/truncation variants plus TShark/C++ byte-recall evaluation; use an ignored output directory. |
| `code/scripts/quic_initial_inventory.py` | Header-only QUIC v1 Initial DCID/SCID inventory by UDP direction; no payload decryption. |
| `code/scripts/l3_proxy_sanity.py` | Extracts SYN/SYN-ACK profiles and conservatively compares manually paired captures; does not calculate JA4T or infer a proxy from MSS/TTL alone. |
| `code/scripts/verify_submission_batch.sh` | One-pass WSL test, manifest, inventory, L3 baseline, and QUIC impairment batch; writes evidence under tracked `results/track2/`. |
| `code/scripts/capture.py` | Explicit, opt-in Track 1 recapture tool; refuses to overwrite committed PCAPs by default. |
| `code/scripts/versions.sh` | Records the lab's JA4/TShark/client tool versions. |
| `code/Dockerfile` | Pinned Linux reference-tool lab image. |
| `Makefile` | Existing core commands plus isolated `lab-image`, `lab-eval`, and `lab-capture` targets. |
| `pyproject.toml`, `requirements.txt` | Current Python project and pytest dependencies; unchanged by Track 1 import. |

## Track 1 documentation and results

| Path | Purpose |
|---|---|
| `docs/tests/T0_lab_checks.md`–`T7_ech_dns.md` | Test rationale, reported observations, and limits. These are teammate-supplied; see the audit before citing claims. |
| `docs/tests/README.md` | T0–T7 index. |
| `docs/track1-evidence-audit.md` | Cross-checks, provenance, known discrepancies, and next reproduction commands. |
| `GLOSSARY.md`, `PHASES.md`, `PRESENTATION_GUIDE.md`, `VIVA_QUESTIONS.md` | Adopted Track 1 learning/presentation guides, updated where imported statements needed qualification. |
| `results/summary.md`, `results/summary.json` | Audited imported summary; zero-packet IPv6 is not counted as tool agreement. |
| `results/imported/yash-summary.*` | Unmodified teammate summary snapshot for traceability. |
| `results/raw/<capture-id>.json` | Imported raw analysis output for each of the 15 Track 1 captures. |
| `results/versions.txt` | Team-supplied Docker tool versions. |
| `results/checkpoint_build_test.txt` | Teammate-supplied C++/pytest/sanitizer log; exact source SHA is not recorded. |
| `results/track1/` | Import provenance, capture-log context, and privacy-trimmed ECH page observations. |
| `results/track2/` | Reproducible QUIC header inventory plus explicitly user-reported paired-probe summary; raw WSL PCAPs/JSON are not yet present. |
| `results/reproduced/` | Ignored outputs from a fresh reference run; copy reviewed artifacts to tracked results before submission. |
| `results/evaluation.json` | Current manifest/evidence status, separate from the Track 1 analysis summary. |

## Reproduction

```sh
make test
make check
make eval
make lab-image
make lab-eval
```

Live packet capture is intentionally separate and requires explicit consent/confirmation:

```sh
make lab-capture CAPTURE_ID=quic_chromium
```

New captures go to `captures/reproduced/` and are not registered automatically. Review hashes, packet counts, metadata, and sensitivity before adding one to the evidence manifest. Never commit key logs.
