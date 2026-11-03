# Experiment scripts

Python code here orchestrates external tools, validates the capture manifest, computes statistics, and emits generated report data. Scripts must not hand-author experimental numbers. Add each capture and its reproduction commands to `captures/manifest.json` before reporting a result.

Current scripts:

- `preflight.py` records available tools, versions, capture interfaces, and TShark protocol/fingerprint fields. It does not capture packets or claim results.
- `evaluate.py` validates the manifest and emits a status summary.

Tool runners, fingerprint comparisons, and statistics are planned but not yet implemented.
