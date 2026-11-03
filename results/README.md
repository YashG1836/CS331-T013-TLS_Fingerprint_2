# Generated results

`baseline/` contains the team-supplied raw FoxIO/TShark outputs for the provisional QUIC capture; they have not been rerun by the current baseline script. `preflight.json` and `verification-status.md` are imported WSL environment/test logs. `make preflight` writes a new environment snapshot to `preflight-current.json` so it does not overwrite the supplied log. `make eval` writes `evaluation.json` with validated/provisional corpus status only; it does not infer L1 or calculate final statistics. Regenerate derived analysis outputs; never hand-edit measured values.
