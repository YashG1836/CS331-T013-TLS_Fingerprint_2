# CN Project 2 — reproducible fingerprinting study

This repository is being rebuilt around the Project 2 research question: where do deployed TLS fingerprints stop being useful, and why? The custom systems component targets QUIC v1 Initial packet processing in C++20. Python is reserved for experiment-manifest validation, orchestration, and evaluation. JA4+/TShark are reference tools; because the FoxIO Rust CLI invokes TShark, their outputs are not fully independent packet decoders.

## Team reading guide and implementation plan

- [`docs/reading-guide.md`](docs/reading-guide.md): concepts and RFC sections behind the QUIC extractor, fingerprint families, and experiments.
- [`docs/quic-baseline.md`](docs/quic-baseline.md): the original QUIC v1 reference capture and its provenance.
- [`docs/track1-evidence-audit.md`](docs/track1-evidence-audit.md): cross-check of Yash's 15-capture Track 1 import, known discrepancies, and reproduction caveats.
- [`docs/track2-integration-plan.md`](docs/track2-integration-plan.md): current PCAP-to-modular-C++ status and controlled follow-up measurements.
- [`docs/l3-contribution-plan.md`](docs/l3-contribution-plan.md): secondary L3 capture-vantage limitation investigation and evidence boundaries.
- [`docs/original-contribution-plan.md`](docs/original-contribution-plan.md): stateful QUIC Initial association/accounting investigation, previous recovery-disposition evidence, and measurement gates.
- [`docs/landscape.md`](docs/landscape.md): preliminary fingerprint-family landscape and prior-art review scaffold.
- [`docs/verification-batch.md`](docs/verification-batch.md): one-pass WSL verification and evidence-collection procedure.
- [`DECISIONS.md`](DECISIONS.md): evidence-based working decisions and human approval gates (not a signed team record).
- [`docs/tests/README.md`](docs/tests/README.md): imported T0–T7 empirical-lab explanations.
- [`GLOSSARY.md`](GLOSSARY.md), [`PHASES.md`](PHASES.md), [`FILES_GUIDE.md`](FILES_GUIDE.md), [`VIVA_QUESTIONS.md`](VIVA_QUESTIONS.md), [`PRESENTATION_GUIDE.md`](PRESENTATION_GUIDE.md): adopted learning and presentation guides.
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): architecture, roles, evidence requirements, acceptance gates, and schedule.

## Current implementation status

Implemented in this first increment:

- QUIC v1 long-header/datagram boundary parser, including variable-length integers.
- QUIC v1 client Initial key derivation using OpenSSL 3 and RFC 9001 test-vector validation.
- Initial header-protection removal and AES-128-GCM authenticated decryption.
- Parsing of Initial PADDING, PING, ACK/ACK_ECN, CRYPTO, and CONNECTION_CLOSE frames.
- Offset-aware CRYPTO reassembly with out-of-order, duplicate, conflicting-overlap, and size-limit handling; incomplete-flow output includes missing CRYPTO byte ranges when the declared ClientHello length is available.
- Bounds-checked TLS ClientHello structure and selected extension parsing.
- Classic-PCAP v2.x Ethernet UDP adapter for unfragmented IPv4/IPv6, with explicit unsupported-case reporting.
- `--pcap` legacy CLI for client Initials plus an opt-in `--stateful-initial-context` mode that associates v1 client/server Initials on a fixed UDP 4-tuple, retains the original client DCID, learns server-SCID aliases, and reports separate directional packet-number/decryption counters; the existing `--hex` mode remains available.
- Lightweight C++ tests, pytest manifest/script validation, a deterministic QUIC PCAP impairment harness, and CMake/CI configuration.

The repository registers the earlier aioquic baseline plus all 15 Track 1 capture attempts and teammate-supplied analysis. Fourteen of Yash's PCAPs contain packets; the IPv6 file is empty and is not treated as a comparison. The full Track 1 tool suite remains imported/provisional and has not been rerun here. The user-run WSL verification batch is now committed at `results/track2/verification-batch-20261104-201936/`; its hashes and result JSON were inspected in this checkout. It reports 54/54 exact-byte multiset matches between C++ and TShark across two QUIC traces and six cases each. The WSL run was not independently reproduced in Arena, and TShark is the reference on each same PCAP variant. The earlier standalone `tls.handshake_raw` export/script is not retained separately. See the Track 1 audit, verification status, and Track 2 plan for provenance and caveats.

Still incomplete or unclaimed: QUIC v2, Retry processing, tuple migration/reuse, PCAPNG, custom JA4 output, final limitation conclusions, and an approved original contribution. The user reports a post-change WSL CMake/CTest/pytest run passed (CTest 1/1, pytest 51/51), with Chromium client Initial decrypts improving 10/16→16/16 and curl 10/20→20/20; five switched-DCID alias buckets account for 6/10 failed packet records, respectively. Complete ClientHello counts were 5/5 in both modes. These post-change logs are not yet retained in the repository, and the supplied summary does not include a byte-for-byte stateful comparison against TShark 4.6.4. Treat the metrics as user-reported until those artifacts are archived; this is packet-level accounting improvement, not increased extraction recall or a validated novelty claim. L3 remains secondary: three container/Wi-Fi probe pairs are timing-correlated, but the bridge capture failed and the intermediate mechanism is unresolved. See `docs/quic/implementation-status.md` and `docs/l3-contribution-plan.md`. The PCAP adapter remains limited to classic Ethernet PCAP and supported unfragmented IPv4/IPv6 UDP.

## Requirements

- C++20 compiler
- CMake 3.20+
- OpenSSL 3.x development headers/libraries
- Python 3.12 for the declared project environment (the current tests use only standard-library features and pytest)

On Debian/Ubuntu, install CMake, a C++ compiler, `libssl-dev`, and pytest. Reference experiments additionally need TShark (4.0.6 or later), a capture tool (`tcpdump` or `dumpcap`), and the pinned FoxIO JA4+ CLI; see [`docs/quic-baseline.md`](docs/quic-baseline.md).

## Commands

```sh
make preflight             # record tools/fields to results/preflight-current.json (preserves imported snapshot)
make build                 # CMake configure and C++ build
make test                  # C++ tests and Python tests
make check                 # validate captures/manifest references
make eval                  # emit provisional/evidence status; no limitation conclusions are inferred
make baseline CAPTURE_ID=<id>  # run existing single-capture reference runner
make lab-image              # build Yash's pinned TShark/FoxIO lab
make lab-eval               # reanalyze Track 1 captures into results/reproduced/
make lab-versions            # record the lab toolchain under results/reproduced/
# Live capture is opt-in and writes to captures/reproduced/:
make lab-capture CAPTURE_ID=quic_chromium
```

For sanitizer builds:

```sh
cmake -S . -B build -DQUIC_ENABLE_SANITIZERS=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

The CLI accepts a single UDP datagram as hex or a supported classic Ethernet PCAP:

```sh
build/code/quic/src/quic-fingerprint --hex '<hex bytes>'
build/code/quic/src/quic-fingerprint --pcap captures/pcaps/quic_chromium.pcap
build/code/quic/src/quic-fingerprint --pcap captures/pcaps/quic_curl.pcap
build/code/quic/src/quic-fingerprint --pcap captures/pcaps/quic_chromium.pcap --stateful-initial-context
```

Hex mode reports packet boundaries and processes a complete decryptable Initial datagram. PCAP mode defaults to UDP service port 443 and can be changed with `--destination-port <port>`. Legacy mode reports per-DCID diagnostics. `--stateful-initial-context` reports per-direction and per-connection Initial counts, DCID-keyed client baseline successes/failures, stateful decrypt results, switched-alias buckets separately from alias packet counts, and ClientHello hex. It is a fixed-4-tuple Initial association, not a complete QUIC migration/Retry implementation or a verified JA4 implementation. The user reports positive WSL client-decryption counts and passing tests; raw outputs, omitted server/per-connection metrics, and an explicit post-stateful byte comparison against TShark 4.6.4 still need to be archived.

## Evidence and result integrity

`captures/manifest.json` is the source of truth. It registers 16 records: the original QUIC baseline and all 15 Track 1 capture attempts, with hashes, metadata, recipes, and output paths. `make check` validates hashes/metadata/artifacts and reports packet-bearing versus empty files; `make eval` reports evidence status only. The Track 1 summary and raw outputs are imported as supplied, except the audited summary marks the zero-packet IPv6 comparison as not applicable. `make lab-eval` is the fresh reference-tool rerun and writes separately under `results/reproduced/`.

## Design boundaries

- C++ handles QUIC packet parsing, cryptographic packet processing, frame parsing, reassembly, and TLS handshake extraction.
- OpenSSL supplies cryptographic primitives; this project does not implement AES, HMAC, or HKDF primitives itself.
- Python handles research orchestration, corpus validation, comparison, and generated reporting data.
- JA4 construction will be integrated only after its QUIC protocol code and field construction have been checked against a verified reference and the specification. Disclose shared decoder dependencies; the supplied FoxIO/TShark CLIs are not fully independent packet decoders. The custom parser does not yet emit a JA4 string.
- Unsupported packet types, frame types, malformed lengths, and incomplete handshakes fail explicitly instead of yielding partial fingerprints.
