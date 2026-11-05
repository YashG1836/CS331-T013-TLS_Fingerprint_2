# L3 candidate: capture-vantage and proxy-aware JA4T attribution

## Status and research question

**Secondary limitation investigation; not a contribution claim.** QUIC Initial connection/CID association is the primary engineering investigation. The committed 5 November batch includes three manually timing-correlated container-to-Wi-Fi probe pairs, and the reviewed manifest/checker classify all three as `separate_tcp_legs_or_sequence_rewrite`. This supports an observed handshake difference across those two capture points, but the bridge capture failed, the probe tuple is absent from WSL `eth0` and vEthernet SYN rows, and Wi-Fi is an adapter capture rather than a physical-wire tap. The intermediate path and mechanism are unresolved; no proxy identity, JA4T/JA4TS impact, or OS misclassification is established.

> Can paired captures at documented points around a local proxy or virtual-network boundary identify when a passive TCP fingerprint describes the adjacent TCP endpoint rather than the intended remote peer?

Use precise language: a proxy does not necessarily “corrupt” JA4T. JA4T describes the TCP stack visible at the capture point; a terminating proxy can replace the TCP connection and therefore change which endpoint the fingerprint represents. A single MSS value (including the reported 65495) is a clue to investigate, not proof of proxying.

## User-reported initial evidence (4 November 2026)

The committed WSL batch at `results/track2/verification-batch-20261104-201936/` contains the TShark 4.6.4 SYN analysis and source PCAP hashes. In each of the two separate offload captures, three complete streams have the same SYN profiles:

| Capture | Client SYN MSS / TTL | SYN-ACK MSS / TTL | SYN/SYN-ACK frame length |
|---|---:|---:|---:|
| TSO/GSO on | 1460 / 64 | 65495 / 63 | 74 bytes each |
| TSO/GSO off | 1460 / 64 | 65495 / 63 | 74 bytes each |

The full profile is client `MSS/window-scale/window/TTL = 1460/10/64240/64` and peer `65495/7/65408/63`; each SYN/SYN-ACK has IP length 60 bytes. The batch analyzer flags same-capture MSS, window-scale, and window asymmetry and explicitly says not to infer a proxy from one capture. These are separate Docker-side, single-vantage traces with client address `172.17.0.2`, not a paired WSL/outer capture. The interface and Docker Desktop topology reports remain user-supplied context; neither shows a paired outside leg, so the observed SYN-ACK values do **not** establish that Docker Desktop generated them.

MSS 65495 is not syntactically impossible: it equals 65535 minus the minimum 20-byte IPv4 and 20-byte TCP headers, and is compatible with an endpoint advertising a very large receive segment size. Advertised MSS is not an observed frame size or a guarantee about path MTU. TTL 63 is consistent with a one-hop decrement from 64 but does not identify the sender's initial TTL or prove proxying. The repeated values across the two captures support that the observed SYN profile did not change with the offload toggle; they do not establish the source stack's identity. The claim that Cloudflare never advertises this value needs independent support and must not be stated as fact from these rows alone.

### Follow-up evidence reported 5 November 2026 (commit `c28a486`)

The user reports running the checker with TShark 4.6.4 on the two imported offload PCAPs and reports the expanded pytest suite passed 36/36 in WSL. Each PCAP yielded six SYN/SYN-ACK observations across three streams; every stream had a complete handshake. Across all three streams per capture, the reported client SYN profile was MSS 1460, window scale 10, window 64240, TTL 64; the peer SYN-ACK profile was MSS 65495, window scale 7, window 65408, TTL 63. The checker flagged same-capture differences in MSS, window scale, and window. It correctly made no cross-capture pairing. The user's JSON remains user-reported and is not present in this checkout; Arena did not rerun TShark on the PCAPs.

The same WSL inventory reports default bridge configuration `docker0` for `172.17.0.0/16` (`172.17.0.1` gateway), but `docker0` was **DOWN** at inventory time. Two other bridges (`br-0670013d5ec3` at `172.18.0.1/16`, and `br-3cd2d23489f7` at `172.19.0.1/16`) and two veth interfaces were UP; WSL `eth0` was `192.168.38.227/20`, with the default route via `192.168.32.1`. This inventory does not map the active veths to containers or show any packets crossing a proxy. In particular, the user's statement that traffic then traverses a host proxy is a hypothesis, not a conclusion established by these interface/route outputs. Inspect the active Docker network/container mapping and capture the same request at simultaneous points before identifying a TCP-terminating proxy.
### Later paired-probe result (user-reported, 5 November 2026)

The user reports a probe with 27 packets in `container-eth0.pcap` and 80 packets in `wsl-eth0.pcap`. The reported container handshake was `172.17.0.3:42910 -> 104.16.123.96:443`: client SYN MSS 1460, window scale 10, window 64240, TTL 64; peer SYN-ACK MSS 1460, window scale 7, window 29184, TTL 63. Same-capture option differences were window scale and window, not MSS. The user reports the corresponding container flow did not appear on WSL `eth0`.

This rules out WSL `eth0` as the outer observation point for this particular probe, assuming the reported capture filter and timing were correct. The explanation that Docker Desktop's sibling utility VM routes through a Windows Hyper-V path is the user's topology hypothesis; no Windows-side PCAP, interface capture, bridge-PCAP count, hash, or original JSON was supplied to verify it. The summary is retained (explicitly as a transcription, not raw evidence) in `results/track2/l3-paired-probe-c28a486.md`. Next, capture simultaneously on the container/active Linux bridge and a Windows host vEthernet/physical interface, then correlate both TCP legs. A native-Linux host is an alternative control.

## Committed paired-vantage run (5 November 2026)

The source captures, their `SHA256SUMS`, and user-run `syn-analysis.json` are committed under `results/l3_paired_batch/` at `a1bd864`. From that directory, `sha256sum -c SHA256SUMS` passes for the four source captures. The analysis reports TShark 4.6.4 and contains the per-stream records. The reviewed `pair_manifest.json` and derived `paired-comparison.json` are additions in this worktree: they pair the three sequential container probes to the Wi-Fi observations by trial order, destination `104.16.124.96:443`, and close timestamps. The reviewed files currently hash to `pair_manifest.json` `d94e1a4b0d74fb24f26b48a48cb9999a13110977fad70d5a4590eea799e84589` and `paired-comparison.json` `99b9a0a9f84e874003b648ff50ea368d773d40216b93eb6eac2287f1369d5b92`. This checkout did not rerun TShark because it is unavailable here.

| Probe | Container stream | Wi-Fi stream | Client SYN Δ (Wi-Fi − container) | SYN-ACK Δ (Wi-Fi − container) | Container ISN → Wi-Fi ISN | Result |
|---|---:|---:|---:|---:|---:|---|
| 1 | 0 | 17 | +9.0258 ms | +38.5 μs | `3419821880` → `168828592` | `separate_tcp_legs_or_sequence_rewrite` |
| 2 | 1 | 18 | +2.4835 ms | −297.0 μs | `873293130` → `2452441281` | `separate_tcp_legs_or_sequence_rewrite` |
| 3 | 2 | 19 | +2.8898 ms | −455.0 μs | `3297501543` → `3298253372` | `separate_tcp_legs_or_sequence_rewrite` |

The container and Wi-Fi SYNs in these pairs have the same destination IP/port and closely aligned SYN/SYN-ACK times, supporting the manual trial correlation. The container profile is client MSS/window-scale/TTL `1460/10/64`; its peer SYN-ACK is `1460/7/63`. At the Windows Wi-Fi adapter, the client profile is `1460/8/128`; the peer SYN-ACK is `1400/13/52`. Source ports and both initial sequence numbers differ across each pair. These are observations of distinct handshake tuples/sequence spaces; they are not proof that one packet's fields were rewritten. MSS 65495 does **not** occur in this paired run; it remains only in the earlier unpaired offload captures.

Important capture limitations from the committed logs and JSON:

- `container-eth0.pcap` has three complete SYN/SYN-ACK streams to `104.16.124.96:443`; `windows-wifi.pcapng` contains the three closely timed observations above, plus unrelated traffic.
- `wsl-eth0.pcap` is 188 bytes; tcpdump reports two packets captured and the saved SYN analysis finds zero SYN rows. Do not summarize this as a zero-packet PCAP.
- The vEthernet capture contains 175 packets and eight SYN observations across four streams, but none is the paired probe to `104.16.124.96`; it includes other traffic. Do not say the interface captured zero packets overall.
- The bridge attempt failed with `tcpdump: br-l3p135735: No such device exists`; `bridge-interface.txt` is empty. There is no bridge-vantage PCAP from this run.
- The host Wi-Fi capture is an adapter capture, not a physical-wire tap. The reported capture logs show no packet drops on the two Windows interfaces.

The evidence supports a **repeatable difference across the observed container and Wi-Fi TCP handshakes for these three controlled requests**, consistent with separate TCP legs or sequence rewriting. The unavailable bridge capture and absence of the probe on WSL `eth0`/the captured vEthernet mean the intermediate point and mechanism remain unresolved. The checker does not calculate JA4T/JA4TS; there is no measured fingerprint output or demonstrated OS misclassification. Keep L3 as a secondary limitation investigation, not a confirmed proxy detector or final contribution claim.

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

The latest inventory had `docker0` **DOWN** while two custom bridges and their veths were UP, so do not assume `docker0` is the active inner point. The command below recreates a short-lived, uniquely named bridge and captures the container/bridge plus WSL `eth0`; the user has already reported that WSL `eth0` did not see the probe. Do not treat it as the outer leg. Re-run the inner/bridge capture only at the same time as Windows-host vEthernet/physical captures. The command saves scratch output under ignored results and removes only its own temporary container/network.

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

Inspect the streams and verify the controlled request before writing any pair manifest. For the next run, list Windows capture interfaces using Wireshark's `dumpcap` from an elevated PowerShell window:

```powershell
$dumpcap = Join-Path $env:ProgramFiles 'Wireshark\dumpcap.exe'
& $dumpcap -D
```

Choose the Windows vEthernet/WSL-facing interface and the physical adapter from that list. In two elevated PowerShell windows, start a 45-second capture on each (replace the example interface numbers with the IDs from `dumpcap -D`), then run the WSL container/bridge probe while both are active:

```powershell
New-Item -ItemType Directory -Force C:\Temp | Out-Null
$dumpcap = Join-Path $env:ProgramFiles 'Wireshark\dumpcap.exe'
& $dumpcap -i 5 -a duration:45 -f 'tcp port 443' -w C:\Temp\l3-vethernet.pcapng
```

```powershell
New-Item -ItemType Directory -Force C:\Temp | Out-Null
$dumpcap = Join-Path $env:ProgramFiles 'Wireshark\dumpcap.exe'
& $dumpcap -i 4 -a duration:45 -f 'tcp port 443' -w C:\Temp\l3-physical.pcapng
```

After a privacy review, copy the Windows captures from WSL's mounted C: drive plus the inner captures and JSON into a tracked `results/track2/l3-paired-<run-id>/` directory, and write `sha256sum` output there. The original `.pcapng` files and the user-run WSL JSON/cases are not currently present in this checkout; a transcribed summary is not a substitute for those raw artifacts. Only pair streams after verifying the same controlled transaction and both handshake directions at each point. Different TCP legs do not alone prove that a particular host proxy caused them. The imported offload-on/off PCAPs remain separate runs and must not be entered as a paired transaction.
