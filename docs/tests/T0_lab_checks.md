# T0: Lab and script checks

**Question:** before trusting Track 1 output, check the lab recipes, scripts, and Track 2 code.

## What is checked

- The modular C++ QUIC project builds and its lightweight CTest target runs.
- The repository pytest suite covers manifest/hash validation, reference runner behavior, and Track 1 helper scripts.
- Track 1 capture IDs and command placeholders are valid.
- Tool versions are recorded in `results/versions.txt` for Yash's Docker lab.

## Commands

For the current repository and a locally installed CMake/OpenSSL toolchain:

```sh
make test
make check
```

When the Docker lab is available:

```sh
make lab-image
make lab-eval
```

The imported Yash capture of its C++ test run is preserved at `results/checkpoint_build_test.txt`.

## Imported result and scope

The teammate log reports the C++ build completed, 1/1 CTest target passed, 9 pytest tests passed, and 1/1 sanitizer CTest target passed. T0 also records four Track 1 script checks. The captured output does not state the exact repository source SHA, so it is corroborating team evidence, not proof about every later commit.

The current branch's own `make test` and CI outcomes are separate and should be recorded in `results/verification-status.md` after changes. A Track 1 tool check does not prove correctness of our C++ PCAP/flow extractor; that integration is still pending.
