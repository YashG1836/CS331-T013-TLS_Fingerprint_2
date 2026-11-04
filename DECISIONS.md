# Working decisions and rationale

**Updated:** 5 November 2026
**Status:** Repository working record; not a signed or unanimous team decision. Human/team approval and rubric review remain open.

## 1. Keep QUIC extraction as a validated engineering baseline, not the original contribution

The tested QUIC v1 implementation recovered five ClientHellos from each committed Chromium/curl capture, with a user-reported exact-byte set match against TShark. The user-reported impairment matrix did not demonstrate a recovery gap against TShark. Missing-range diagnostics accurately label unknown expected lengths as observed-extent-only; baseline correlation later identified one Chromium suffix beyond the damaged capture's observed extent and no curl suffix. This is an expected information limit when the ClientHello length header is absent, not an established diagnostic defect.

A header-only inventory now explains the five extra per-DCID failure buckets per trace: they are later client-to-server Initial packets using the server's Initial SCID as a switched DCID, while the current CLI derives from each packet's current DCID. These are not server-direction decrypt attempts. This identifies a protocol-context limitation in the current per-DCID extractor, but the user-reported ClientHello comparison shows no missed ClientHello in the tested captures. See `docs/quic/implementation-status.md` and `results/track2/quic-initial-dcid-inventory.json`.

## 2. Investigate L3 capture-vantage attribution provisionally

The imported offload captures show a stable, single-capture SYN/SYN-ACK profile difference. The user's controlled container probe reports a different peer MSS (1460) and reports that its connection did not appear on WSL `eth0`. This supports investigating where packets are visible; it does **not** establish a proxy, TCP termination, or a JA4T error. The user-provided Docker Desktop utility-VM explanation is a topology hypothesis pending a synchronized Windows-side capture or equivalent evidence. `docs/l3-contribution-plan.md` defines the gate and keeps TSO/GSO separate.

## 3. Preserve the existing tool boundaries

- C++ remains the QUIC packet/Initial decryption/frame/CRYPTO/TLS parsing implementation and owns protocol-level unit tests.
- Python remains the experiment/reference orchestration layer: deterministic PCAP mutation, TShark comparison, evidence manifests, and conservative SYN/SYN-ACK capture summaries.
- The L3 checker does not implement JA4T/JA4TS and does not label a proxy from MSS, TTL, or a single vantage. A fingerprint implementation/version must be pinned before comparing strings.
- Source captures remain immutable. Reproduction scratch output may be generated under ignored `results/reproduced/`, but any submission evidence must be copied to a tracked `results/track1/` or `results/track2/` path with source hashes, exact commands, versions, provenance, and privacy review. Never fabricate or hand-transcribe a raw output as though it were original.

## 4. Evidence and approval gates

Before presenting L3 as an original contribution, obtain a correlated, simultaneous view at a known boundary (including Windows physical/vEthernet if WSL `eth0` does not see the flow), distinguish NAT from TCP termination, repeat the probe, review prior art, and check the course rubric. Raw WSL PCAPs/JSON not present in this checkout remain user-reported; this record is not a replacement for them.

The architectural and research choices above are working decisions recorded from the available evidence, not a claim that the team held or approved a meeting. Team ownership, final contribution choice, course-rubric interpretation, and report wording require human confirmation.
