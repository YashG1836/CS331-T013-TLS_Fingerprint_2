# QUIC reference-tool baseline

**Status:** procedure prepared; no project capture has been run through the reference tools. `captures/manifest.json` is empty, and the sandbox currently has neither TShark nor the FoxIO `ja4` executable. Do not treat the official JA4 repository's sample pcaps as this project's captured evidence.

## Reference versions

- FoxIO JA4+ Rust CLI: pin the `v0.18.6` source tag at commit `4490e6c5d317cbc6662005ad9482a4b994e320a9`. Record the installed binary's `ja4 --version` output with the experiment. The upstream project documents the CLI invocation `ja4 -j -r <pcap>` for JSON output with raw fields.
- Wireshark TShark: the FoxIO README states TShark 4.0.6 or later is required for full functionality. Record the exact `tshark --version` output used; do not assume field presence from the version number. `make preflight` checks actual QUIC and JA3/JA4 field abbreviations.

Upstream references checked 3 November 2026:

- [FoxIO JA4+ repository](https://github.com/FoxIO-LLC/ja4)
- [FoxIO Rust CLI usage](https://github.com/FoxIO-LLC/ja4/blob/v0.18.6/rust/README.md)
- [Wireshark/TShark](https://www.wireshark.org/docs/man-pages/tshark.html)

## Baseline procedure

1. Use a controlled, non-sensitive QUIC v1 client connection. Capture only project-related traffic. Never capture personal browsing or commit public-session TLS key logs.
2. Review the pcap and add a matching record to `captures/manifest.json`, including capture provenance, client and server, commands, versions, interface/vantage, and the expected protocol properties. The file must exist under `captures/pcaps/`.
3. Run `make preflight PYTHON=python3`. Confirm the actual TShark field availability and that both TShark and `ja4` are on `PATH`.
4. Run `make baseline CAPTURE_ID=<registered-id> PYTHON=python3`.
5. The script writes `results/reference/<registered-id>.json`. It records the pcap SHA-256, executable versions, exact argument vectors, TShark fields, exit codes, and raw tool outputs. It does **not** decide whether outputs agree or establish a limitation; interpret the values only after checking the same packets/flows and preserving the output as experiment evidence.
6. If a command fails or a field is missing, keep that as a tool observation with the exact version and reproduction command. Do not rewrite a missing field as “QUIC is confidential.” QUIC v1 Initial protection and TLS handshake confidentiality are different questions; see RFC 9001 §§5.2–5.3 and RFC 8446 §4.4.

The script runs FoxIO as `ja4 -j -r <capture>` and TShark with `-T fields`, selecting only fields actually reported by that TShark build. When the tool's QUIC fields, JA4 fields, or output schemas differ, preserve the raw results and record the discrepancy; do not silently normalize it away.
