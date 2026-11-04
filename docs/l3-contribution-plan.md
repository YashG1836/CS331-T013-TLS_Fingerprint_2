# L3 candidate: capture-vantage and proxy-aware JA4T attribution

## Status and research question

**Primary candidate to investigate; not yet a contribution claim.** QUIC Initial recovery is not the candidate for the tested impairment matrix: the user reports identical C++/TShark outputs. The user-reported QUIC damaged-flow audit shows three incomplete statuses per trace and no material diagnostic gap. Baseline correlation finds no missing suffix for the unknown-length curl flow and shows that Chromium's unknown-length flow is missing `[1026,1891)` beyond its observed extent; the C++ tool correctly marks that length as unknown. L3 is now the primary contribution candidate because the imported T3 evidence suggests TCP fields observed inside Docker may belong to a nearby proxy/virtual-network stack rather than the remote endpoint. User-reported SYN rows show the MSS asymmetry, but their TSV/raw PCAP is not retained here, the frame-size narrative conflicts with aggregate data, and there is no paired outer capture.

> Can paired captures at documented points around a local proxy or virtual-network boundary identify when a passive TCP fingerprint describes the adjacent TCP endpoint rather than the intended remote peer?

Use precise language: a proxy does not necessarily “corrupt” JA4T. JA4T describes the TCP stack visible at the capture point; a terminating proxy can replace the TCP connection and therefore change which endpoint the fingerprint represents. A single MSS value (including the reported 65495) is a clue to investigate, not proof of proxying.

## User-reported initial evidence (4 November 2026)

The user reports rerunning the imported captures with TShark 4.6.4. Both offload conditions have the same SYN values:

| Capture | Client SYN MSS / TTL | SYN-ACK MSS / TTL | SYN/SYN-ACK frame length |
|---|---:|---:|---:|
| TSO/GSO on | 1460 / 64 | 65495 / 63 | 74 bytes each |
| TSO/GSO off | 1460 / 64 | 65495 / 63 | 74 bytes each |

The traces are from a Docker-side capture with client address `172.17.0.2`; these are single-vantage observations re-exported by the user, not a paired WSL/outer capture. The user initially reported WSL `eth0` MTU 1500, Docker bridges/veth interfaces present, `docker0` down, and Docker Desktop integration inactive; in a later report, Docker Desktop 4.97.0 / Engine 29.9.2 was started and WSL integration became active, with the default bridge at `172.17.0.0/16` and container address `172.17.0.2`. Neither report includes a paired outside capture, so the MSS values do **not** yet establish that Docker Desktop generated the SYN-ACK.

MSS 65495 is not syntactically impossible: it equals 65535 minus the minimum 20-byte IPv4 and 20-byte TCP headers, and is compatible with an endpoint advertising a very large receive segment size. Advertised MSS is not an observed frame size or a guarantee about path MTU. TTL 63 is consistent with a one-hop decrement from 64 but does not identify the sender's initial TTL or prove proxying. The repeated values across the two captures support that the observed SYN profile did not change with the offload toggle; they do not establish the source stack's identity. The claim that Cloudflare never advertises this value needs independent support and must not be stated as fact from these rows alone.

### Follow-up evidence reported 5 November 2026 (commit `c28a486`)

The user reports running the checker with TShark 4.6.4 on the two imported offload PCAPs and reports the expanded pytest suite passed 36/36 in WSL. Each PCAP yielded six SYN/SYN-ACK observations across three streams; every stream had a complete handshake. Across all three streams per capture, the reported client SYN profile was MSS 1460, window scale 10, window 64240, TTL 64; the peer SYN-ACK profile was MSS 65495, window scale 7, window 65408, TTL 63. The checker flagged same-capture differences in MSS, window scale, and window. It correctly made no cross-capture pairing. The user's JSON remains user-reported and is not present in this checkout; Arena did not rerun TShark on the PCAPs.

The same WSL inventory reports default bridge configuration `docker0` for `172.17.0.0/16` (`172.17.0.1` gateway), but `docker0` was **DOWN** at inventory time. Two other bridges (`br-0670013d5ec3` at `172.18.0.1/16`, and `br-3cd2d23489f7` at `172.19.0.1/16`) and two veth interfaces were UP; WSL `eth0` was `192.168.38.227/20`, with the default route via `192.168.32.1`. This inventory does not map the active veths to containers or show any packets crossing a proxy. In particular, the user's statement that traffic then traverses a host proxy is a hypothesis, not a conclusion established by these interface/route outputs. Inspect the active Docker network/container mapping and capture the same request at simultaneous points before identifying a TCP-terminating proxy.
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

The first checker should be conservative and label the capture evidence, not assert proxy identity from one field. The scaffold outputs per-capture profiles and, for manually correlated paired streams, labels such as `same_tcp_handshake`, `same_tcp_handshake_with_tuple_translation`, `same_sequence_option_rewrite_or_measurement_mismatch`, `separate_tcp_legs_or_sequence_rewrite`, `insufficient_correlation`, and `incomplete_capture`. None is a proxy confirmation.

Synthetic unit-test cases for the classifier (not empirical evidence):

1. Same TCP handshake observed at both points, same sequence numbers and SYN options → do not flag termination.
2. Address/port translation with the same handshake sequence/options → classify as translation/unresolved, not termination.
3. Two correlated TCP legs with distinct initial sequence numbers and changed SYN options, captured on opposite sides of a known boundary → label `separate_tcp_legs_or_sequence_rewrite`; do not call this confirmed termination and retain both endpoint profiles.
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

The user now reports Docker Desktop 4.97.0 / Engine 29.9.2 with WSL integration active. Before capturing, obtain the actual Linux bridge name (`docker network inspect bridge --format '{{json .Options}}'`) and confirm which WSL interfaces see the container's traffic. A WSL `eth0` capture is not automatically a wire-side view of Docker Desktop's Windows-side networking; if the suspected TCP termination is on Windows, a Windows-host capture may be required.

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

Review the SYN versus SYN-ACK rows for endpoint/port tuples and option differences. The standard-library scaffold can produce a machine-readable version from those PCAPs:

```sh
python3 code/scripts/l3_proxy_sanity.py \
  --capture offload_on=captures/pcaps/tls_offload_on.pcap \
  --capture offload_off=captures/pcaps/tls_offload_off.pcap \
  --tshark tshark \
  --output results/reproduced/l3/offload-syn-analysis.json
```

The two offload files are separate runs, not paired vantage observations. The tool therefore reports their per-capture SYN profiles and marks the cross-capture relation as unpaired; it will not infer a proxy. It extracts raw SYN/SYN-ACK details but does **not** calculate JA4T/JA4TS.

For future paired captures, a manually reviewed pairing manifest can compare streams across two labels. Example schema (replace streams and labels with IDs from the JSON reports; only set the booleans after documenting the capture points and same-request correlation):

```json
{
  "schema_version": 1,
  "pairs": [{
    "pair_id": "request-01",
    "same_transaction_confirmed": true,
    "capture_points_bracket_boundary": true,
    "left": {"capture": "container", "stream": "3"},
    "right": {"capture": "wsl-eth0", "stream": "7"}
  }]
}
```

Then add `--pair-manifest results/reproduced/l3/pairs.json`. It requires SYN and SYN-ACK on both legs and emits conservative labels such as same handshake/tuple translation, sequence or option mismatch, separate TCP legs, or insufficient evidence. Even a `separate_tcp_legs_or_sequence_rewrite` result is not proxy proof by itself.

The latest inventory has `docker0` **DOWN** while two custom bridges and their veths are UP, so do not use `--network bridge` or assume `docker0` is the active inner point. Create a short-lived, uniquely named bridge for one controlled request. This brackets the container and Linux bridge, while WSL `eth0` remains only a *candidate* outer observation—not a proven wire-side point. The command also saves all outputs under the ignored results directory and removes only the temporary container/network it creates.

```sh
set -euo pipefail

docker image inspect cn-lab >/dev/null 2>&1 || make lab-image
stamp=$(date +%s)
net="l3probe-${stamp}"
bridge="br-l3p${stamp: -6}"
container="l3probe-${stamp}"
out="$PWD/results/reproduced/l3/paired-${stamp}"
mkdir -p "$out"
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  docker network rm "$net" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create --driver bridge \
  --opt "com.docker.network.bridge.name=$bridge" "$net"
docker run -d --name "$container" --network "$net" --cap-add NET_RAW \
  -v "$out:/out" --entrypoint sh cn-lab -c 'sleep 60'
docker network inspect "$net" --format '{{json .Options}} {{json .IPAM.Config}}'
ip -br link show "$bridge"

sudo timeout --preserve-status -s INT 30s tcpdump -i "$bridge" -nn -s 0 -U \
  -w "$out/bridge.pcap" 'tcp port 443' &
bridge_capture_pid=$!
sudo timeout --preserve-status -s INT 30s tcpdump -i eth0 -nn -s 0 -U \
  -w "$out/wsl-eth0.pcap" 'tcp port 443' &
eth0_capture_pid=$!
sleep 2

set +e
docker exec "$container" sh -c '
  tcpdump -i eth0 -nn -s 0 -U -w /out/container-eth0.pcap "tcp port 443" &
  capture_pid=$!
  sleep 2
  curl -4 --http1.1 --connect-timeout 8 --max-time 15 -sS -o /dev/null \
    "https://www.cloudflare.com/cdn-cgi/trace?l3audit=$(date +%s%N)"
  curl_status=$?
  sleep 2
  kill -INT "$capture_pid" 2>/dev/null || true
  wait "$capture_pid"
  exit "$curl_status"
'
probe_status=$?
set -e
wait "$bridge_capture_pid"
wait "$eth0_capture_pid"
printf 'Probe exit status: %s\nCaptures: %s\n' "$probe_status" "$out"
if [ "$probe_status" -ne 0 ]; then
  echo "Probe failed; retain the PCAPs for troubleshooting." >&2
  exit "$probe_status"
fi
```

The probe is network-active; run it only when authorized. It waits up to 30 seconds for host captures, then cleans up the temporary container and network while retaining the PCAPs. Analyze all three captures without auto-pairing first:

```sh
python3 code/scripts/l3_proxy_sanity.py \
  --capture container="$out/container-eth0.pcap" \
  --capture bridge="$out/bridge.pcap" \
  --capture wsl_eth0="$out/wsl-eth0.pcap" \
  --tshark tshark --output "$out/syn-analysis.json"
```

Inspect the streams and verify a matching destination and the controlled request before writing any pair manifest. If WSL `eth0` contains no corresponding flow, or only a gateway-side connection, do not call it the outer leg; capture the Windows host's physical/vEthernet interface with an approved Windows tool. Even distinct TCP legs in simultaneous captures do not alone prove that a particular host proxy caused them. The two imported offload PCAPs remain separate runs and must not be entered as a paired transaction.
