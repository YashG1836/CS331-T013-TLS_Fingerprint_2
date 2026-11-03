# QUIC v1 reference-tool baseline procedure

## Snapshot provenance

`results/preflight.json` is the team-supplied WSL preflight snapshot dated 3 November 2026 at 13:08 UTC. It reports TShark/Wireshark 4.6.4, OpenSSL 3.5.5, CMake 4.2.3, GCC 15.2.0, Python 3.14.4, tcpdump 4.99.6, and a `ja4` executable reporting 0.18.6. It enumerates QUIC, JA3, and JA4 fields but explicitly does not verify capture permissions. This snapshot predates the capture at 13:11 UTC.

The archived capture and reference outputs are in the repository now. The pcap hash and pcapng structure were checked during integration, but TShark and JA4 have not been rerun in this checkout. See [`results/verification-status.md`](../results/verification-status.md) and [`docs/quic-baseline.md`](quic-baseline.md).

## Pinned reference

Use the FoxIO Rust JA4+ source release `v1.0.1`, tag commit `896b951e438c2979e0ef077a94ad390b1c973c23`, with TShark 4.0.6 or later. The supplied run reports the binary version as `0.18.6` and records its SHA-256 in capture metadata; an attestation tying the executable to that commit is still missing. Record both the source release and binary version. FoxIO's Rust CLI invokes TShark, so disclose their shared dissection dependency.

## Capture and comparison steps

For each new capture:

1. Use one controlled, non-sensitive client action. The supplied example used aioquic 1.7.2 with ALPN `h3` to request `https://cloudflare.com`; the exact script and invocation were not retained. Do not add personal browsing, credentials, or key logs.
2. Record the capture interface, filter, start/stop, tool versions, server address, and client command in `captures/metadata/<id>.json`.
3. Register it in `captures/manifest.json`, including the capture SHA-256, metadata path, provenance state, and paths to stored baseline outputs.
4. Run the pinned FoxIO JA4+ binary and TShark on the **same pcap bytes**. Preserve the exact commands and raw outputs. The supplied commands are recorded verbatim in the baseline metadata and `results/baseline/`.
5. Run `make check` to validate the capture hash, metadata, and artifact references. Run `make eval` to get a status summary; this does not rerun TShark or infer a limitation.
6. To create a fresh machine-readable run with this repository's current command conventions, use:

   ```sh
   make baseline CAPTURE_ID=<registered-id> PYTHON=python
   ```

   The runner records the capture hash, tool versions, exact argv, discovered TShark fields, exit codes, and raw outputs under `results/reference/`. Its commands differ from the supplied TSV/JSON run, so do not overwrite or relabel the archived outputs as runner-generated.

A matching JA4 from these two tools on one capture is a baseline observation, not proof of full independence or a broad no-gap result. In this sample, both tools reported `q13d0307h3_55b375c5d22e_1cecd519fee8`; FoxIO's TShark dependency weakens independence. The capture does not demonstrate an L1 tool-coverage gap. The missing provenance and byte-level ClientHello validation still need follow-up.
