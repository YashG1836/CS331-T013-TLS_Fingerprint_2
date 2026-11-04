# CN Project 2 — reproducible fingerprinting study

This repository is being rebuilt around the Project 2 research question: where do deployed TLS fingerprints stop being useful, and why? The custom systems component targets QUIC v1 Initial packet processing in C++20. Python is reserved for experiment-manifest validation, orchestration, and evaluation. JA4+/TShark are reference tools; because the FoxIO Rust CLI invokes TShark, their outputs are not fully independent packet decoders.

## Team reading guide and implementation plan

- [`docs/reading-guide.md`](docs/reading-guide.md): concepts and RFC sections behind the QUIC extractor, fingerprint families, and experiments.
- [`docs/quic-baseline.md`](docs/quic-baseline.md): the original QUIC v1 reference capture and its provenance.
- [`docs/track1-evidence-audit.md`](docs/track1-evidence-audit.md): cross-check of Yash's 15-capture Track 1 import, known discrepancies, and reproduction caveats.
- [`docs/track2-integration-plan.md`](docs/track2-integration-plan.md): current PCAP-to-modular-C++ status and controlled follow-up measurements.
- [`docs/l3-contribution-plan.md`](docs/l3-contribution-plan.md): primary L3 capture-vantage/proxy-aware JA4T candidate and evidence gates.
- [`docs/original-contribution-plan.md`](docs/original-contribution-plan.md): QUIC recovery candidate disposition and bounded damaged-flow diagnostic audit.
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
- `--pcap` CLI integration for QUIC v1 client Initial decryption, per-DCID CRYPTO reassembly, and full ClientHello hex output; the existing `--hex` mode remains available.
- Lightweight C++ tests, pytest manifest/script validation, a deterministic QUIC PCAP impairment harness, and CMake/CI configuration.

The repository registers the earlier aioquic baseline plus all 15 Track 1 capture attempts and teammate-supplied analysis. Fourteen of Yash's PCAPs contain packets; the IPv6 file is empty and is not treated as a comparison. The full Track 1 tool suite remains imported/provisional and has not been rerun here. The user separately reports a direct Ubuntu WSL TShark `tls.handshake_raw` comparison: the current C++ CLI's five ClientHellos from each of the two QUIC captures match all ten raw references byte-for-byte by set equality. The raw exports/comparison script are not yet retained in the repository. See the Track 1 audit, verification status, and Track 2 plan for provenance and caveats.

Still incomplete or unclaimed: a complete bidirectional connection/migration model and original-DCID context across CID switches; retention of the raw byte-comparison exports and impairment case JSON; QUIC v2; Retry processing; custom JA4 output; final limitation conclusions; and an approved original contribution. The user reports WSL tests for the incomplete-flow range diagnostics and an exact-byte impairment comparison, but their raw logs remain absent. The committed header-only DCID inventory explains five extra per-DCID failure buckets as later client Initials after a CID switch; it does not show a missed ClientHello in the tested samples. L3 proxy-aware capture-vantage attribution remains provisional: the latest user-reported probe did not see the container flow on WSL `eth0`, so a Windows-host capture point is needed before claiming a boundary effect. See `docs/l3-contribution-plan.md`. The PCAP adapter remains limited to classic Ethernet PCAP and supported unfragmented IPv4/IPv6 UDP.

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
```

Hex mode reports packet boundaries and processes a complete decryptable Initial datagram. PCAP mode defaults to destination UDP port 443 and can be changed with `--destination-port <port>`. It reports per-DCID extraction diagnostics and ClientHello hex. This is an early v1 extraction path, not a complete QUIC flow tracker or a verified JA4 implementation.

## Evidence and result integrity

`captures/manifest.json` is the source of truth. It registers 16 records: the original QUIC baseline and all 15 Track 1 capture attempts, with hashes, metadata, recipes, and output paths. `make check` validates hashes/metadata/artifacts and reports packet-bearing versus empty files; `make eval` reports evidence status only. The Track 1 summary and raw outputs are imported as supplied, except the audited summary marks the zero-packet IPv6 comparison as not applicable. `make lab-eval` is the fresh reference-tool rerun and writes separately under `results/reproduced/`.

## Design boundaries

- C++ handles QUIC packet parsing, cryptographic packet processing, frame parsing, reassembly, and TLS handshake extraction.
- OpenSSL supplies cryptographic primitives; this project does not implement AES, HMAC, or HKDF primitives itself.
- Python handles research orchestration, corpus validation, comparison, and generated reporting data.
- JA4 construction will be integrated only after its QUIC protocol code and field construction have been checked against a verified reference and the specification. Disclose shared decoder dependencies; the supplied FoxIO/TShark CLIs are not fully independent packet decoders. The custom parser does not yet emit a JA4 string.
- Unsupported packet types, frame types, malformed lengths, and incomplete handshakes fail explicitly instead of yielding partial fingerprints.
