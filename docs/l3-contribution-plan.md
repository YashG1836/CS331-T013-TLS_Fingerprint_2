# L3 candidate: capture-vantage and proxy-aware JA4T attribution

## Status and research question

**Primary candidate to investigate; not yet a contribution claim.** QUIC Initial recovery is not the candidate for the tested impairment matrix: the user reports identical C++/TShark outputs. The user-reported QUIC damaged-flow audit shows three incomplete statuses per trace; only clean-baseline correlation for one unknown-length flow per trace remains. L3 is now the primary contribution candidate because the imported T3 evidence suggests TCP fields observed inside Docker may belong to a nearby proxy/virtual-network stack rather than the remote endpoint. User-reported SYN rows show the MSS asymmetry, but their TSV/raw PCAP is not retained here, the frame-size narrative conflicts with aggregate data, and there is no paired outer capture.

> Can paired captures at documented points around a local proxy or virtual-network boundary identify when a passive TCP fingerprint describes the adjacent TCP endpoint rather than the intended remote peer?

Use precise language: a proxy does not necessarily “corrupt” JA4T. JA4T describes the TCP stack visible at the capture point; a terminating proxy can replace the TCP connection and therefore change which endpoint the fingerprint represents. A single MSS value (including the reported 65495) is a clue to investigate, not proof of proxying.

## User-reported initial evidence (4 November 2026)

The user reports rerunning the imported captures with TShark 4.6.4. Both offload conditions have the same SYN values:

| Capture | Client SYN MSS / TTL | SYN-ACK MSS / TTL | SYN/SYN-ACK frame length |
|---|---:|---:|---:|
| TSO/GSO on | 1460 / 64 | 65495 / 63 | 74 bytes each |
| TSO/GSO off | 1460 / 64 | 65495 / 63 | 74 bytes each |

The traces are from a Docker-side capture with client address `172.17.0.2`; these are single-vantage observations re-exported by the user, not a paired WSL/outer capture. The user also reports WSL `eth0` MTU 1500, Docker bridges/veth interfaces present, `docker0` down, and Docker Desktop WSL integration not activated. Therefore the values do **not** yet establish that a Docker Desktop proxy generated the SYN-ACK.

MSS 65495 is not syntactically impossible: it equals 65535 minus the minimum 20-byte IPv4 and 20-byte TCP headers, and is compatible with an endpoint advertising a very large receive segment size. Advertised MSS is not an observed frame size or a guarantee about path MTU. TTL 63 is consistent with a one-hop decrement from 64 but does not identify the sender's initial TTL or prove proxying. The repeated values across the two captures support that the observed SYN profile did not change with the offload toggle; they do not establish the source stack's identity. The claim that Cloudflare never advertises this value needs independent support and must not be stated as fact from these rows alone.

## Separate the hypotheses

1. **Capture vantage / TCP termination:** compare SYN and SYN-ACK observations on both accessible sides of the suspected Docker/WSL proxy or translation boundary. If TCP is terminated and recreated, expect different 4-tuples/initial sequence numbers and potentially different SYN options on the two legs. If only NAT is present, do not infer termination merely from address translation.
2. **Segmentation offload:** compare TSO/GSO on versus off while holding the path and endpoint constant. This affects captured segment/frame sizes; it is not itself evidence that SYN MSS options changed. Do not confound the offload experiment with the proxy-vantage experiment.
3. **Fingerprint attribution:** calculate JA4T/JA4TS only with a pinned, documented implementation/specification. If unavailable, report the raw TCP option tuples and do not invent a JA4T string.

## Minimum controlled evidence

- Preserve raw PCAPs, SHA-256 hashes, exact interface names, capture commands, timestamps, routes, MTU/offload state, client/server versions, and TShark version.
- Capture the same connection simultaneously at the closest available inner and outer interfaces. Record when the “outer” point is still only a WSL/Docker virtual interface; do not call it wire-side without evidence.
- Record each SYN and SYN-ACK: frame/time, `tcp.stream`, source/destination addresses and ports, SYN/ACK flags, MSS, window scale, SACK-permitted, timestamp options, TCP window, IP TTL/hop-limit, IP length, TCP length, and frame length.
- Correlate the two legs with a controlled request and timestamps. Do not equate flows solely by translated 5-tuples; a terminating proxy creates separate TCP connections.
- Reconcile the imported T3 narrative (1586-byte frame and 1514+138 split; MSS 65495/1460) with fresh packet-level rows and the aggregate (`biggest_frame` 4913/2962; `pieces_max` 1/2). Explain any difference in filter, layer, point, or definition.
- Evaluate the same path with the offload toggle separately. Keep capture-point and offload settings in the result key.

## Sanity-checker behavior and test cases

The first checker should be conservative and label the capture evidence, not assert proxy identity from one field. Suggested outcomes: `single_vantage_only`, `same_tcp_handshake`, `address_translation_or_unresolved`, `probable_tcp_termination` (only with paired, correlated legs), and `insufficient_or_incomplete_capture`.

Synthetic unit-test cases for the classifier (not empirical evidence):

1. Same TCP handshake observed at both points, same sequence numbers and SYN options → do not flag termination.
2. Address/port translation with the same handshake sequence/options → classify as translation/unresolved, not termination.
3. Two correlated TCP legs with distinct initial sequence numbers and changed SYN options, captured on opposite sides of a known proxy → probable TCP termination; retain both endpoint fingerprints.
4. A lone MSS 65495, TTL 63, or their combination at one point → insufficient evidence; never classify a proxy from these alone.
5. Different frame/segment lengths under TSO/GSO on/off but unchanged SYN options → segmentation/offload observation, not a JA4T change.
6. Missing SYN or SYN-ACK, retransmitted SYNs, or ambiguous flow correlation → mark incomplete/ambiguous and suppress endpoint attribution.

Proceed to implementation only if repeated paired captures show a reproducible attribution failure or ambiguity that a scoped sanity diagnostic can detect, and the diagnostic distinguishes a proxy-adjacent TCP peer from a remote endpoint without overclaiming from MSS/TTL alone. Compare against existing JA4T/JA4TS tools and prior work and check the course rubric before calling it original. If the raw evidence does not reproduce the T3 observation, record the negative result and reject this candidate.

## WSL first-pass commands (read-only against imported captures)

First inventory the available points and tools; do not start a new network capture until interface roles are clear:

```sh
ip -br link
ip -br address
ip route get 1.1.1.1
tshark -D
command -v docker && docker version
```

The user's current WSL report says the Docker Desktop executable is visible but WSL integration is not enabled. If that still holds, enable **Docker Desktop → Settings → Resources → WSL Integration → Ubuntu**, reopen the distro, then confirm `docker version` shows both client and server and inspect `docker network inspect bridge`. Do not start a capture until the container/bridge/WSL/Windows capture points are identified; a WSL `eth0` capture is not automatically a wire-side view of Docker Desktop's Windows-side networking.

Then export SYN/SYN-ACK rows from the two imported offload captures. These commands do not alter the PCAPs; the output is local reproduction data:

```sh
mkdir -p results/reproduced/l3
for id in tls_offload_on tls_offload_off; do
  tshark -r "captures/pcaps/${id}.pcap" \
    -Y 'tcp.flags.syn == 1' -T fields \
    -E header=y -E separator=$'\t' -E occurrence=a -E aggregator=, \
    -e frame.number -e frame.time_epoch -e tcp.stream \
    -e ip.src -e ipv6.src -e tcp.srcport \
    -e ip.dst -e ipv6.dst -e tcp.dstport \
    -e tcp.flags.syn -e tcp.flags.ack -e tcp.options.mss_val \
    -e tcp.options.wscale.shift -e tcp.options.sack_perm \
    -e tcp.options.timestamp.tsval -e tcp.options.timestamp.tsecr \
    -e tcp.window_size_value -e ip.ttl -e ipv6.hlim \
    -e ip.len -e ipv6.plen -e tcp.len -e frame.len \
    > "results/reproduced/l3/${id}-syn.tsv"
done
```

Review the SYN versus SYN-ACK rows for endpoint/port tuples and option differences, then send the interface inventory plus the two TSV files (or a privacy-reviewed excerpt). Based on that inventory, choose the feasible paired capture points and write a specific recapture command. Keep these generated files under ignored `results/reproduced/` until they are reviewed and provenance is complete.
