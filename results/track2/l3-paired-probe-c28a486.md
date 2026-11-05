# Paired probe result — user-reported

**Status:** User-reported from Ubuntu WSL; not independently rerun in Arena. The original PCAPs and JSON output were not supplied to this checkout. This is a transcribed finding summary, not a raw capture artifact.

- Reported run was against checker commit `c28a486`.
- User reports 27 packets in `container-eth0.pcap` and 80 packets in `wsl-eth0.pcap`; a corresponding container flow was not observed on WSL `eth0`.
- Reported container handshake: client `172.17.0.3:42910 -> 104.16.123.96:443`, MSS 1460, window scale 10, window 64240, TTL 64. Peer SYN-ACK: MSS 1460, window scale 7, window 29184, TTL 63. The checker reports same-capture differences in window scale and window, not MSS.
- The user reports Docker Desktop's separate utility-VM / Hyper-V path as the reason WSL `eth0` does not see this flow. The packet observation supports that this capture on WSL `eth0` did not include the corresponding flow; the proposed topology explanation still needs independent interface/packet evidence.
- No bridge-PCAP packet count, raw JSON, PCAP SHA-256, exact command transcript, or synchronized Windows-host capture was supplied. The capture vantage is therefore not yet fully reproducible or proven to bracket a TCP-terminating boundary.

## Interpretation

This negative observation rejects WSL `eth0` as the outer point for this particular reported Docker Desktop probe. It does not by itself prove a proxy or explain where the connection was handled. A Windows-host physical/vEthernet capture, or a native-Linux host capture, is required to observe and correlate the other side. Keep TSO/GSO toggles separate from the vantage experiment. See `docs/planning/l3-contribution-plan.md` for the current plan and evidence gates.
