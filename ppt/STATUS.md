# Presentation status — slide draft prepared

`ppt/slides.md` contains a 12-slide Markdown deck outline with speaker notes, evidence labels, the captured-order QUIC results, stateful reorder sensitivity, L3/TLS caveats, and a final limitations/future-work slide. It is aligned with the evidence generated in `report/report.md` and the batch at `results/track2/verification-batch-20261105-105416/`.

The batch is user-run in Ubuntu WSL against source commit `fa9fcdb`, committed in `7a2584c`, and inspectable in this checkout. CTest 1/1 and pytest 52/52 are recorded. The original-order stateful baselines have 5/5 exact-byte matches per trace against TShark 4.6.4; synthetic reverse/shuffle cases expose statefulness limits. L6 public IPv6 egress remains `NOT_MEASURED`, and the optional local loopback capture check failed. Do not display an overall “all live rows pass” claim.

Before export or presentation:

- Fill in approved team names and course-specific slide requirements.
- Obtain team/rubric approval for the contribution framing.
- Preserve the `WSL BATCH` and `TRACK 1 — imported/team-supplied` provenance labels.
- Do not claim a Wireshark/TShark failure, proxy identity, full QUIC compliance, or novelty.
- Any final PDF/presentation export should be generated from this Markdown only after team review; no export is included in this draft.
