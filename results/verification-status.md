# Verification and tool readiness — imported team log

This record is preserved from the team-provided `cn.zip`, committed in `d71a402`. Its original verification commands were run in the team's Ubuntu WSL workspace. The record is useful evidence about that workspace and its QUIC capture, but its build/test output does **not** validate the current modular C++ code: the archived workspace contains a monolithic `quic.cpp`, a GoogleTest target, and a different Python manifest CLI. The current repository deliberately keeps the modular C++ files, lightweight C++ test harness, pytest, `reference_baseline.py`, and current `evaluate.py` conventions.

## Team-reported build and tests in the archived workspace

- `make test`: the archived tree reportedly built and passed 6 C++/GoogleTest cases and 2 Python `unittest` cases.
- After adding the capture, the archived tree reportedly ran `python3 code/scripts/manifest.py check captures/manifest.json` and reported one provisional capture.
- Those commands are not the current repository's `make test` / `make check` implementation. Do not present these results as a test of the modular implementation. Current-branch verification is provided by the repository's own test suite and GitHub Actions, not by this archived log.

## Team-reported WSL tool snapshot

The archived `results/preflight.json` was checked at `2026-11-03T13:08:18Z` and reports GNU Make 4.4.1, CMake 4.2.3, GCC 15.2.0, OpenSSL 3.5.5, TShark/Wireshark 4.6.4, tcpdump 4.99.6, Python 3.14.4, and FoxIO `ja4` 0.18.6. TShark's field registry includes QUIC, JA3, and JA4 fields. The snapshot explicitly says capture permissions were not independently verified. It predates the capture and baseline output timestamps.

## Team-reported capture and reference outputs

- Capture: `captures/pcaps/quic-v1-baseline.pcapng`; SHA-256 `1cd5f8c05b5b966eed1ae339eeec80b86b830deccda81489dabefb28f272ec7a`.
- The capture metadata reports one controlled aioquic 1.7.2 QUIC v1 / ALPN h3 request to `cloudflare.com`; the exact client script, invocation, and dumpcap command/duration were not retained.
- TShark 4.6.4 reports frame 1 as QUIC v1 Initial with a ClientHello, CRYPTO offset 0 and length 475, JA3 `121f6e4f22ee3205214b0676ed64b9e2`, and JA4 `q13d0307h3_55b375c5d22e_1cecd519fee8`.
- The supplied FoxIO JSON reports the same JA4 for its UDP stream. It reports binary version 0.18.6 and source release v1.0.1; the recorded executable hash is in metadata. The exact installed executable was not included, so the hash/build attestation was not independently checked here.
- The supplied TShark and FoxIO command lines are recorded in the capture metadata. They differ from the current `reference_baseline.py` command set. The TSV and JSON are preserved as supplied team outputs, not regenerated output from this repository's runner.
- FoxIO's Rust CLI invokes TShark; their matching values are a cross-CLI consistency observation, not a fully independent decoder comparison. This capture does **not** demonstrate an L1 tool-coverage gap.

The archive reports a 523-byte Initial within a 1200-byte UDP payload, with 677 trailing zero bytes. It also reports that its monolithic custom parser failed on the full datagram and succeeded on the first QUIC packet. That custom-parser result has not been reproduced against this repository's modular C++ implementation and must not be attributed to it.

## Integration checks performed here

- Recomputed the pcap SHA-256 and matched the manifest, metadata, and supplied `capture_hash.txt`.
- Parsed the pcapng block framing: 30 blocks total, 27 enhanced packet blocks, and no Decryption Secrets Blocks.
- Verified that the supplied FoxIO JA4 equals the first TShark ClientHello JA4 and that the supplied JA3/JA4 row matches the metadata observations.
- TShark and FoxIO were not available in the integration environment, so their commands were **not** rerun here. The capture is consequently registered as provisional; missing provenance and byte-level ClientHello verification remain open.
