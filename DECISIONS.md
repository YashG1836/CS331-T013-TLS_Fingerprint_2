# Working decisions and rationale

**Updated:** 5 November 2026

**Status:** Provisional repository record. This is not a signed or unanimous team decision; team review, course-rubric review, and approval of the final contribution remain open.

## 1. Use C++20 for the bounded QUIC protocol core; keep experiment orchestration in Python

The project keeps the required QUIC depth dive in a small modular C++20 core: classic-PCAP/UDP adaptation, QUIC v1 long-header parsing, Initial key derivation and packet decryption, supported Initial-frame parsing, offset-aware CRYPTO reassembly, and TLS ClientHello validation. C++20 `std::span`, `std::optional`, and `std::string_view` express borrowed byte ranges and absent/partial parse state without forcing copies at each layer. OpenSSL 3 supplies the cryptographic primitives; the build does not add a libpcap dependency. Python remains the experiment layer for deterministic PCAP mutations, TShark comparison, manifests, and conservative SYN/SYN-ACK summaries.

This is an engineering trade-off, not a novelty claim. It gives the byte parser explicit module boundaries and unit-testable functions, but requires careful bounds checks and adds a compiler/CMake/OpenSSL setup requirement. The current adapter intentionally supports only classic PCAP v2 Ethernet with unfragmented IPv4/IPv6 UDP; PCAPNG, VLANs, IP fragments, IPv6 extension chains, QUIC v2, a complete bidirectional connection model, Retry, migration, 0-RTT, every frame type, and JA4 calculation are outside the implemented scope. C++20, modularity, and RFC Initial decryption alone are not an original contribution.

The WSL verification batch at `results/track2/verification-batch-20261104-201936/` records GCC 15.2.0, OpenSSL 3.5.5, TShark 4.6.4, Linux 6.18.33.2 WSL2, CTest 1/1, and pytest 39/39. The batch is user-run evidence: its manifest hashes and JSON structure were checked in this checkout, but the WSL run was not independently regenerated here. The RFC 9001 Initial key test vector remains a separate unit test from capture-level evidence.

## 2. Keep QUIC extraction as a validated engineering baseline; do not claim novel reassembly

The batch evaluates six cases for each of two captures: baseline, reversed packet-record order, fixed-seed shuffle, one selected Initial-CRYPTO record dropped, every third selected Initial-CRYPTO record dropped, and a selected record truncated by 64 captured bytes. For each client, all six comparisons report exact-byte multiset equality with TShark's ClientHello bytes from that same case: 27/27 reference ClientHellos matched, with 0 misses and 0 extras. The every-third-drop case has 2 references and 2 matches, not recovery of the five original hellos. Aggregated: 54/54 reference outputs matched across 12 run-cases. These are batch-artifact-inspected results from a user-run WSL execution, not independent Arena reproduction or external ground truth; TShark is the comparator, and the comparison is conditioned on what TShark emits from each mutated PCAP.

The extractor still reports incomplete flows and Initial decryption failures in these captures. Those statuses must not be conflated with a missed complete ClientHello: the measured comparison found no missing complete TShark output under these tested conditions. The present evidence therefore does not support an extraction/reassembly contribution. Reopen that direction only if a new, independently measured failure appears.

A header-only inventory explains five extra per-DCID decryption-failure buckets in each original trace: later client-to-server Initial packets carry a switched DCID matching a server Initial SCID. They are not server-direction decrypt attempts. RFC 9001 §5.2 derives Initial secrets from the connection's original client Initial DCID (subject to the Retry transition); the current CLI's per-packet/per-DCID simplification instead derives from each packet's current DCID. This is a connection-context limitation, but the five complete ClientHellos per trace still match the batch's TShark reference. See `docs/quic/implementation-status.md` and `results/track2/quic-initial-dcid-inventory.json`.

## 3. Treat L3 capture-vantage attribution as a candidate question, not a proxy finding

The checked WSL batch's TShark 4.6.4 SYN analysis contains three complete SYN/SYN-ACK streams in each of the separate offload-on/off PCAPs (six observations per file). Every client SYN has MSS/window-scale/window/TTL `1460/10/64240/64`; every peer SYN-ACK has `65495/7/65408/63`. The SYN and SYN-ACK IP lengths are 60 bytes and frame lengths 74 bytes; the same-capture options differ in MSS, window scale, and window. The source captures use client `172.17.0.2` and the peer `104.16.124.96`. These are single-vantage observations from two separate captures; they are not paired capture points and the batch explicitly warns against inferring a proxy from one capture.

MSS 65495 is not impossible and is not a path-MTU measurement. It is the advertised receive limit in a TCP MSS option; the value alone does not identify the sender or prove TCP termination. TTL 63 alone likewise does not identify an initial TTL or proxy. A separately reported controlled probe had peer MSS 1460 and the corresponding container flow was absent from WSL `eth0`; this only disqualifies that WSL interface as the outer point for that particular probe, subject to its reported filter/timing. A Windows-side capture and a synchronized pair of observations are still missing. The Docker Desktop utility-VM explanation remains a topology hypothesis.

Continue L3 as the primary *candidate to investigate*, not as a demonstrated JA4T error or novel proxy detector. Capture both sides of a known boundary, correlate the same request and both TCP legs, distinguish NAT from TCP termination, and keep TSO/GSO toggles separate from capture-vantage tests. The checker must label raw features and uncertainty; it must not call a proxy from MSS, TTL, or a lone capture. See `docs/l3-contribution-plan.md`.

## 4. Interpret post-switch QUIC DCIDs under the Initial key schedule, not as direction failures

Five later client Initial DCID buckets in each imported QUIC trace use a DCID equal to a server Initial SCID. The records remain client-to-server; the CLI selects them by UDP destination port 443. RFC 9001 §5.2 uses the original client Initial DCID for Initial secret derivation, with Retry-specific handling. A server-provided replacement DCID does not become the Initial-secret input merely because later client packets use it. These are post-switch key-context failures in the current per-DCID inventory, not server-direction decrypt failures and not evidence that a ClientHello was missed. See [RFC 9001 §5.2](https://www.rfc-editor.org/rfc/rfc9001.html#section-5.2), [RFC 9000 §7.2](https://www.rfc-editor.org/rfc/rfc9000.html#section-7.2), and the checked inventory JSON.

## 5. Evidence, provenance, and approval gates

- `DECISIONS.md` and `docs/landscape.md` are repository working documents; neither represents team approval or a completed comprehensive literature review.
- The committed WSL batch is inspectable and its SHA256 manifest validates, but the run itself remains user-run/imported evidence. Do not describe it as independently reproduced in Arena. Keep the exact tool versions, command lines, source hashes, selected mutation records, raw tool exports, and negative outcomes with the batch.
- Track 1 remains teammate-supplied/imported evidence with the provenance limits in `docs/track1-evidence-audit.md`. Missing key logs and incomplete arms remain missing; never reconstruct them.
- Before promoting L3 as an original contribution, obtain paired raw captures at documented points, separate translation from termination, repeat the controlled probe, review JA4T/JA4TS/p0f and related prior art, and check the course rubric with the team.
- Preserve source captures. Keep reproduction scratch in ignored `results/reproduced/`; promote reviewed evidence only with hashes, exact commands, versions, provenance, and privacy review. Do not commit TLS secrets or fabricate team decisions/results.
- Team ownership, final contribution choice, rubric interpretation, and final claim wording require human confirmation.
