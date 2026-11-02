# CN Project 2 — reproducible fingerprinting study

This repository is being rebuilt around the Project 2 research question: where do deployed TLS fingerprints stop being useful, and why? The custom systems component targets QUIC v1 Initial packet processing in C++20. Python is reserved for experiment-manifest validation, orchestration, and evaluation. Existing JA4+/tshark implementations remain independent reference tools.

## Team reading guide

Start with [`docs/reading-guide.md`](docs/reading-guide.md) for the concepts and RFC sections behind the QUIC extractor, fingerprint families, passive visibility, and the seven limitation experiments.

## Current implementation status

Implemented in this first increment:

- QUIC v1 long-header/datagram boundary parser, including variable-length integers.
- QUIC v1 client Initial key derivation using OpenSSL 3 and RFC 9001 test-vector validation.
- Initial header-protection removal and AES-128-GCM authenticated decryption.
- Parsing of Initial PADDING, PING, ACK/ACK_ECN, CRYPTO, and CONNECTION_CLOSE frames.
- Offset-aware CRYPTO reassembly with out-of-order, duplicate, conflicting-overlap, and size-limit handling.
- Bounds-checked TLS ClientHello structure and selected extension parsing.
- C++ tests and a Python manifest-validation command.

Not yet implemented or claimed: pcap/UDP extraction, TCP baseline experiments, QUIC v2, Retry processing, reference-tool integration, JA4 output, real client corpus, seven measured limitations, or any experimental conclusion. The repository currently contains no evidence captures. The CLI takes a single datagram encoded as hex and initially targets client Initial packets. These scope limits are explicit so a scaffold is not mistaken for measured research.

## Requirements

- C++20 compiler
- CMake 3.20+
- OpenSSL 3.x development headers/libraries
- Python 3.12 for the declared project environment (the current tests use only standard-library features and pytest)

On Debian/Ubuntu, install CMake, a C++ compiler, `libssl-dev`, and pytest.

## Commands

```sh
make build                 # CMake configure and C++ build
make test                  # C++ tests and Python tests
make check                 # validate corpus/manifest references
make eval                  # emit results/evaluation.json (no numbers until evidence exists)
```

For sanitizer builds:

```sh
cmake -S . -B build -DQUIC_ENABLE_SANITIZERS=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

The first-stage CLI accepts one UDP datagram as hex:

```sh
build/src/quic_fingerprint/quic-fingerprint --hex '<hex bytes>'
```

It prints packet boundaries and, if the input includes a decryptable client Initial and complete ClientHello, reports parsed field counts and the recovered handshake bytes. Do not interpret this CLI's input mode as pcap support.

## Evidence and result integrity

`corpus/manifest.json` is the initial source of truth. It intentionally has zero capture records until packet evidence and its provenance are available. `make eval` therefore emits an explicit `no_evidence_yet` status rather than fabricated measurements. Every future capture must have its conditions, exact commands, tools/versions, and expected properties recorded in the manifest before a result is quoted in the report.

## Design boundaries

- C++ handles QUIC packet parsing, cryptographic packet processing, frame parsing, reassembly, and TLS handshake extraction.
- OpenSSL supplies cryptographic primitives; this project does not implement AES, HMAC, or HKDF primitives itself.
- Python handles research orchestration, corpus validation, comparison, and generated reporting data.
- JA4 construction will be integrated only after its QUIC protocol code and field construction have been checked against the selected independent reference implementation. The custom parser does not yet emit a JA4 string.
- Unsupported packet types, frame types, malformed lengths, and incomplete handshakes fail explicitly instead of yielding partial fingerprints.
