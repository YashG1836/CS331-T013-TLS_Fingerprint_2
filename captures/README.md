# Capture corpus

- Put reviewed packet captures under `pcaps/` and one metadata JSON record per capture under `metadata/`.
- Register each capture in `manifest.json`; measured results must regenerate from those files.
- Store TLS key logs in `keylogs/` only for controlled, non-sensitive lab captures. The directory and `*.keys`/`*.keylog` files are ignored by Git by default. Never commit key logs from public-site or personal browsing sessions.
- Do not capture credentials or personal traffic. Inspect a capture and its metadata before adding it to version control.

The corpus contains one team-supplied QUIC v1 reference capture registered as provisional L1 baseline evidence. Its TShark and FoxIO JA4 outputs match for the ClientHello in this capture, so it does not demonstrate an L1 tool-coverage gap. Its exact capture/client commands and independent ClientHello-byte validation remain incomplete; see `docs/quic-baseline.md` and `LEDGER.md`. Do not treat this provisional baseline as a final limitation result.
