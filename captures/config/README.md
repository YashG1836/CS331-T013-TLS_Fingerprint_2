# Chromium test policies

These two managed-policy JSON files were imported to reproduce the teammate's T7 conditions: `ech_off_policy.json` disables ECH, and `doh_policy.json` configures encrypted DNS. The supplied ECH-off/on page responses are summarized in `results/track1/page-observations.md`; the ECH+DoH page did not load in the imported run. Policies are copied into the temporary lab container by the recorded recipe and do not alter the host system.
