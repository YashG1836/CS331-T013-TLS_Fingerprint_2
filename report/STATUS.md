# Report status — draft prepared

`report/report.md` is a formal, evidence-bounded draft. Quantitative results tables are generated from the committed WSL evaluation batch with `python3 report/build_report.py`; the generator reads the environment/build log, stateless and stateful per-trace JSON, and seven-row JSON. The source template is `report/report.template.md`.

The 5 November batch was run in Ubuntu WSL against source commit `fa9fcdb` and committed as evidence in `7a2584c` at `results/track2/verification-batch-20261105-105416/`. The report records CTest 1/1, pytest 52/52, stateful captured-order baseline accounting and TShark 4.6.4 byte-multiset equality. It also discloses stateful reverse/shuffle sensitivity, the L6 public-egress `NOT_MEASURED` status, and the failed local `::1` capture attempt. This is user-run evidence inspected from committed artifacts, not an independent Arena reproduction.

Before treating the report as final:

- Fill in approved author names and any course-specific title/format requirements.
- Obtain team approval and check the actual course rubric.
- Keep Track 1 TLS results labeled imported/team-supplied.
- Review the targeted prior-art discussion; the literature survey is not systematic.
- Do not claim full QUIC compliance, order-independent extraction, a new fingerprint detector, or public IPv6 measurement.
- Generate the Results block again after any evidence changes using `python3 report/build_report.py`.

No PDF is generated in this draft. `report/report.md` is the editable source deliverable.