# L3 candidate: capture-vantage and proxy-aware JA4T attribution

## Status and research question

**Primary candidate to investigate; not yet a contribution claim.** QUIC Initial recovery is not the candidate for the tested impairment matrix: the user reports identical C++/TShark outputs. A small QUIC damaged-flow diagnostic audit remains a separate correctness check. L3 is now the primary contribution candidate because the imported T3 evidence suggests TCP fields observed inside Docker may belong to a nearby proxy/virtual-network stack rather than the remote endpoint, but the raw SYN rows and imported frame-size narrative are missing or inconsistent.

> Can paired captures at documented points around a local proxy or virtual-network boundary identify when a passive TCP fingerprint describes the adjacent TCP endpoint rather than the intended remote peer?

Use precise language: a proxy does not necessarily “corrupt” JA4T. JA4T describes the TCP stack visible at the capture point; a terminating proxy can replace the TCP connection and therefore change which endpoint the fingerprint represents. A single MSS value (including the reported 65495) is a clue to investigate, not proof of proxying.

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

## Decision gate

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
