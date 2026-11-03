# Capture corpus

- Put reviewed packet captures under `pcaps/` and one metadata JSON record per capture under `metadata/`.
- Register each capture in `manifest.json`; measured results must regenerate from those files.
- Store TLS key logs in `keylogs/` only for controlled, non-sensitive lab captures. The directory and `*.keys`/`*.keylog` files are ignored by Git by default. Never commit key logs from public-site or personal browsing sessions.
- Do not capture credentials or personal traffic. Inspect a capture and its metadata before adding it to version control.

There are no evidence captures in the corpus yet; do not treat an empty directory as an experiment result.
