# Imported Track 1 artifacts

These files derive from Yash's repository snapshot at commit `b1ffd7c65ae47af1b62184549262ef838c4a234d`. The imported zip SHA-256 is `044fe1a27924cb63e13a26708f1a8d402454d49e3fa7ca8547f8fac28f2f603e`.

- `../raw/<id>.json` contains the supplied TShark/FoxIO output records.
- `../imported/yash-summary.json` and `.md` preserve the teammate's original summary unchanged.
- `../summary.json` and `.md` are reviewed derivatives. The empty IPv6 pcap is marked not comparable rather than falsely reporting that two empty outputs agree.
- `../versions.txt` and `../checkpoint_build_test.txt` are supplied environment/test logs, not logs generated during this integration.
- `capture-log.md` summarizes the imported capture log; the workstation's absolute path was redacted.
- `page-observations.md` preserves the relevant ECH page fields while omitting unrelated local network identifiers.

No TLS key-log files were imported. See [`docs/track1-evidence-audit.md`](../../docs/track1-evidence-audit.md) for the validation, discrepancies, and limitations.
