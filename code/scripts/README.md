# Experiment scripts

Python code here orchestrates external tools, validates the capture manifest, computes statistics, and emits generated report data. Scripts must not hand-author experimental numbers. Add each capture and its reproduction commands to `captures/manifest.json` before reporting a result.

Current script: `evaluate.py` validates the manifest and emits a status summary. Tool runners, fingerprint comparisons, and statistics are planned but not yet implemented.
