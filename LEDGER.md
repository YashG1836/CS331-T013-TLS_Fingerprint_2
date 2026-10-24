# Limitation ledger — evidence status

This is an experiment checklist, not a results section. No packet captures are currently committed, so none of the rows below is an observed finding and no numerical conclusion is claimed. Each row stays open until a capture, exact reproduction command, tool versions, and RFC section citations are linked.

| ID | Hypothesis to test | Minimum evidence needed | Status |
|---|---|---|---|
| L1 | QUIC Initial recovery requires key derivation, protected-header removal, packet decryption, CRYPTO extraction, and offset-aware reassembly; reference tools may not expose the same ClientHello. | Real QUIC v1 capture; custom recovered ClientHello; independent decoder/reference output on identical bytes; reproduction command and failure cases. | Open — no capture |
| L2 | JA4X/JA4H visibility depends on having the relevant TLS plaintext/secrets. | Same traffic and metadata with/without key log; outputs from the reference tools; exact tool versions. | Open — no capture |
| L3 | JA4T and packet-level observations depend on capture vantage point and network path. | Matched client/relay/proxy captures with interface, offload, NAT, MTU and tool metadata. | Open — no capture |
| L4 | Large hybrid key shares may affect ClientHello size and segmentation, but a negotiated key-exchange group and resulting fields must be verified before drawing conclusions. | Paired captures, negotiated group evidence, packet sizes/counts and fingerprint comparison. | Open — no capture |
| L5 | JA3 may vary across repeated handshakes while normalized JA4 may be more stable; applications sharing a TLS stack may collide. | Repeated captures per client plus two controlled applications, measured by scripts from committed evidence. | Open — no capture |
| L6 | IP family may leave TLS-only JA4 unchanged while affecting transport/correlation observations. | Matched IPv4/IPv6 captures, addresses and capture conditions, regenerated fingerprints. | Open — no capture |
| L7 | ECH and encrypted DNS may reduce hostname attribution; they must not be described as changing a TLS fingerprint unless the capture proves that. | Genuine supported ECH traffic or explicitly labelled simulation; DNS condition, tool output and attribution analysis. | Open — no capture |

Certificate compression/abridging remains a forward-looking watch item unless real deployed traffic is captured. A simulation must never be labelled as an observed network result.
