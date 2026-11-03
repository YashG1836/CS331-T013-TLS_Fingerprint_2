# CN Project 2 — reproducible fingerprinting study

This repository is being rebuilt around the Project 2 research question: where do deployed TLS fingerprints stop being useful, and why? The custom systems component targets QUIC v1 Initial packet processing in C++20. Python is reserved for experiment-manifest validation, orchestration, and evaluation. JA4+/TShark are reference tools; because the FoxIO Rust CLI invokes TShark, their outputs are not fully independent packet decoders.

## Team reading guide and implementation plan

- [`docs/reading-guide.md`](docs/reading-guide.md): concepts and RFC sections behind the QUIC extractor, fingerprint families, and experiments.
- [`docs/quic-baseline.md`](docs/quic-baseline.md): pinned reference-tool versions and reproducible baseline procedure.
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): architecture, implementation stages, evidence requirements, acceptance gates, and the proposed schedule.

## Current implementation status

Implemented in this first increment:

- QUIC v1 long-header/datagram boundary parser, including variable-length integers.
- QUIC v1 client Initial key derivation using OpenSSL 3 and RFC 9001 test-vector validation.
- Initial header-protection removal and AES-128-GCM authenticated decryption.
- Parsing of Initial PADDING, PING, ACK/ACK_ECN, CRYPTO, and CONNECTION_CLOSE frames.
- Offset-aware CRYPTO reassembly with out-of-order, duplicate, conflicting-overlap, and size-limit handling.
- Bounds-checked TLS ClientHello structure and selected extension parsing.
- C++ tests and a Python manifest-validation command.

One team-supplied QUIC v1 capture with TShark and FoxIO outputs is now registered as **provisional** evidence. Their first-frame JA4 values match, so this capture does not demonstrate an L1 tool-coverage gap. The imported commands have not been rerun by the current runner, provenance is incomplete, and the archive's monolithic-parser result is not a test of this repository's modular C++ implementation.

Not yet implemented or claimed: pcap/UDP extraction, TCP baseline experiments, QUIC v2, Retry processing, custom JA4 output, a multi-client corpus, seven measured limitations, or an original solution. The CLI takes a single datagram encoded as hex and initially targets client Initial packets. These boundaries prevent a scaffold or one provisional baseline from being mistaken for a complete result.

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
make baseline CAPTURE_ID=<id>  # run FoxIO JA4+ and TShark on one registered pcap
```

For sanitizer builds:

```sh
cmake -S . -B build -DQUIC_ENABLE_SANITIZERS=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

The first-stage CLI accepts one UDP datagram as hex:

```sh
build/code/quic/src/quic-fingerprint --hex '<hex bytes>'
```

It prints packet boundaries and, if the input includes a decryptable client Initial and complete ClientHello, reports parsed field counts and the recovered handshake bytes. Do not interpret this CLI's input mode as pcap support.

## Evidence and result integrity

`captures/manifest.json` is the source of truth. It contains one provisional QUIC v1 reference capture with a verified SHA-256 and linked metadata/baseline files. `make check` verifies the capture, hash, metadata, and artifact paths; `make eval` reports provisional status and does not infer a limitation or generate fingerprint statistics. The team must resolve the missing provenance and independently verify the recovered ClientHello before using this as a final L1 finding.

## Design boundaries

- C++ handles QUIC packet parsing, cryptographic packet processing, frame parsing, reassembly, and TLS handshake extraction.
- OpenSSL supplies cryptographic primitives; this project does not implement AES, HMAC, or HKDF primitives itself.
- Python handles research orchestration, corpus validation, comparison, and generated reporting data.
- JA4 construction will be integrated only after its QUIC protocol code and field construction have been checked against a verified reference and the specification. Disclose shared decoder dependencies; the supplied FoxIO/TShark CLIs are not fully independent packet decoders. The custom parser does not yet emit a JA4 string.
- Unsupported packet types, frame types, malformed lengths, and incomplete handshakes fail explicitly instead of yielding partial fingerprints.
