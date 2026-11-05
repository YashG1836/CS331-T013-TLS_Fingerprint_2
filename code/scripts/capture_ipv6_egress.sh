#!/usr/bin/env bash
# Capture a direct IPv6 TLS ClientHello plus an IPv4 control on the same Linux host.
# This cannot manufacture global IPv6 connectivity: without a global route, it records NOT_MEASURED.
set -uo pipefail

if [[ $# -lt 1 || $# -gt 2 || ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  cat <<'USAGE'
Usage: sudo code/scripts/capture_ipv6_egress.sh results/track2/l6_ipv6_<run-id> [hostname]

Creates packet captures, curl endpoint logs, interface/route/tool snapshots, TShark
ClientHello/SYN extracts, a status file, and SHA256SUMS. Default hostname: example.com.
Use a network with working global IPv6. Loopback is not a substitute for IPv6 egress.
The script never modifies captures/pcaps/. Review privacy before committing output.
USAGE
  [[ $# -eq 0 || ${1:-} == "-h" || ${1:-} == "--help" ]] && exit 0
  exit 2
fi

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)
cd "$repo_root"
run_dir=$(realpath -m -- "$1")
hostname=${2:-example.com}
if [[ ! "$hostname" =~ ^[A-Za-z0-9.-]+$ ]]; then
  echo "hostname must be a DNS name containing only letters, digits, dots, or hyphens" >&2
  exit 2
fi
case "$run_dir" in
  "$repo_root"/results/track2/l6_ipv6_*) ;;
  *) echo "output must resolve under results/track2/l6_ipv6_/: $run_dir" >&2; exit 2 ;;
esac
if [[ -e "$run_dir" ]]; then
  echo "output directory already exists: $run_dir" >&2
  exit 2
fi
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "run under sudo/root for tcpdump capture permissions" >&2
  exit 2
fi
for tool in ip curl tcpdump tshark sha256sum getent; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "required tool not found: $tool" >&2
    exit 2
  fi
done

mkdir -p "$run_dir"
{
  printf 'timestamp_utc=%s\n' "$(date -u --iso-8601=seconds)"
  printf 'hostname=%s\n' "$hostname"
  printf 'kernel='; uname -a
  printf '\n-- tools --\n'
  curl --version | head -n 1
  tcpdump --version 2>&1 | head -n 1
  tshark --version | head -n 1
  printf '\n-- addresses and routes --\n'
  ip -6 addr show
  ip -6 route show
  ip -4 route show
} > "$run_dir/environment.txt" 2>&1

probe_v6=2606:4700:4700::1111
route6=$(ip -6 route get "$probe_v6" 2>&1)
route_rc=$?
printf '%s\n' "$route6" > "$run_dir/ipv6-route-probe.txt"
if [[ $route_rc -ne 0 ]]; then
  printf 'L6_PUBLIC_EGRESS=NOT_MEASURED\nreason=no IPv6 route to global probe address\n' > "$run_dir/l6-status.txt"
  (cd "$run_dir" && sha256sum environment.txt ipv6-route-probe.txt l6-status.txt > SHA256SUMS)
  echo "IPv6 is not routed on this uplink; recorded NOT_MEASURED at $run_dir"
  exit 2
fi
iface=$(awk '{for(i=1;i<=NF;i++) if ($i=="dev") {print $(i+1); exit}}' <<<"$route6")
src6=$(awk '{for(i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}' <<<"$route6")
if [[ -z "$iface" || -z "$src6" || ! "$src6" =~ ^[23] ]]; then
  printf 'L6_PUBLIC_EGRESS=NOT_MEASURED\nreason=route did not select a global-unicast IPv6 source\ninterface=%s\nsource=%s\n' "$iface" "$src6" > "$run_dir/l6-status.txt"
  (cd "$run_dir" && sha256sum environment.txt ipv6-route-probe.txt l6-status.txt > SHA256SUMS)
  echo "No global-unicast IPv6 source selected; recorded NOT_MEASURED at $run_dir"
  exit 2
fi
target6=$(getent ahostsv6 "$hostname" | awk '$1 ~ /:/ {print $1; exit}')
target4=$(getent ahostsv4 "$hostname" | awk '$1 ~ /^[0-9.]+$/ {print $1; exit}')
if [[ -z "$target6" || ! "$target6" =~ ^[23] ]]; then
  printf 'L6_PUBLIC_EGRESS=NOT_MEASURED\nreason=hostname has no resolvable global-unicast IPv6 address\nhostname=%s\ntarget_ipv6=%s\n' "$hostname" "$target6" > "$run_dir/l6-status.txt"
  (cd "$run_dir" && sha256sum environment.txt ipv6-route-probe.txt l6-status.txt > SHA256SUMS)
  echo "No global-unicast IPv6 address resolved for $hostname; recorded NOT_MEASURED at $run_dir"
  exit 2
fi
printf 'capture_interface=%s\nsource_ipv6=%s\nroute_probe=%s\nhostname=%s\ntarget_ipv6=%s\ntarget_ipv4=%s\n' \\
  "$iface" "$src6" "$probe_v6" "$hostname" "$target6" "$target4" > "$run_dir/capture-point.txt"

capture_arm() {
  local family=$1
  local bpf=$2
  local resolve_address=$3
  local pcap="$run_dir/ipv${family}-control.pcap"
  local curl_log="$run_dir/ipv${family}-curl.txt"
  local tcpdump_log="$run_dir/ipv${family}-tcpdump.txt"
  tcpdump -i "$iface" -s 0 -U -w "$pcap" "$bpf" >/dev/null 2>"$tcpdump_log" &
  local capture_pid=$!
  sleep 1
  if ! kill -0 "$capture_pid" 2>/dev/null; then
    wait "$capture_pid" 2>/dev/null
    printf 'tcpdump failed to start for IPv%s\n' "$family" > "$curl_log"
    return 1
  fi
  set +e
  curl --noproxy '*' "-$family" --resolve "$hostname:443:$resolve_address" \
    --connect-timeout 10 --max-time 30 --silent --show-error \
    --output /dev/null \
    --write-out 'url=%{url_effective}\nremote_ip=%{remote_ip}\nhttp_code=%{http_code}\nssl_verify_result=%{ssl_verify_result}\n' \
    "https://$hostname/" > "$curl_log" 2>&1
  local curl_rc=$?
  kill -INT "$capture_pid" 2>/dev/null
  wait "$capture_pid" 2>/dev/null
  local tcpdump_rc=$?
  set -e
  printf 'curl_exit_code=%s\ntcpdump_exit_code=%s\n' "$curl_rc" "$tcpdump_rc" >> "$curl_log"
  return 0
}

set -e
capture_arm 6 "ip6 and host $target6 and tcp port 443" "[$target6]" || true
if [[ -n "$target4" ]]; then
  capture_arm 4 "ip and host $target4 and tcp port 443" "$target4" || true
else
  printf 'hostname has no resolvable IPv4 address\n' > "$run_dir/ipv4-control-missing.txt"
fi

for family in 6 4; do
  pcap="$run_dir/ipv${family}-control.pcap"
  if [[ "$family" == 6 ]]; then display_ip=ipv6; else display_ip=ip; fi
  if [[ -s "$pcap" ]]; then
    set +e
    tshark -r "$pcap" -Y "$display_ip && tcp.flags.syn == 1" -T fields -E header=y -E separator=$'\t' \
      -e frame.number -e ip.src -e ip.dst -e ipv6.src -e ipv6.dst -e tcp.srcport -e tcp.dstport \
      -e tcp.flags.ack -e tcp.options.mss_val -e tcp.options.wscale.shift -e frame.len \
      > "$run_dir/ipv${family}-syn.tsv" 2> "$run_dir/ipv${family}-syn.stderr.txt"
    tshark -r "$pcap" -Y "$display_ip && tls.handshake.type == 1" -T fields -E header=y -E separator=$'\t' \
      -e frame.number -e ip.src -e ip.dst -e ipv6.src -e ipv6.dst -e tcp.srcport -e tcp.dstport \
      -e tls.handshake.extensions_server_name -e tls.handshake.ja4 -e tls.handshake.length \
      > "$run_dir/ipv${family}-clienthello.tsv" 2> "$run_dir/ipv${family}-clienthello.stderr.txt"
    tshark_rc=$?
    set -e
    printf 'tshark_extract_exit_code=%s\n' "$tshark_rc" >> "$run_dir/ipv${family}-curl.txt"
  else
    printf 'No packet-bearing capture for IPv%s\n' "$family" > "$run_dir/ipv${family}-capture-missing.txt"
  fi
done

v6_hellos=0
if [[ -s "$run_dir/ipv6-clienthello.tsv" ]]; then
  v6_hellos=$(awk 'NR>1 && NF {n++} END {print n+0}' "$run_dir/ipv6-clienthello.tsv")
fi
curl6_rc=$(awk -F= '/^curl_exit_code=/{print $2}' "$run_dir/ipv6-curl.txt" 2>/dev/null | tail -n 1)
tshark6_rc=$(awk -F= '/^tshark_extract_exit_code=/{print $2}' "$run_dir/ipv6-curl.txt" 2>/dev/null | tail -n 1)
if [[ ${curl6_rc:-1} == 0 && ${tshark6_rc:-1} == 0 && $v6_hellos -gt 0 ]]; then
  l6_status=CAPTURED_REVIEW_REQUIRED
  reason='direct IPv6 TLS ClientHello captured; compare with IPv4 control and review target/route before interpretation'
else
  l6_status=NOT_MEASURED
  reason='no successful direct IPv6 TLS ClientHello was confirmed'
fi
{
  printf 'L6_PUBLIC_EGRESS=%s\n' "$l6_status"
  printf 'reason=%s\n' "$reason"
  printf 'interface=%s\nsource_ipv6=%s\nhostname=%s\n' "$iface" "$src6" "$hostname"
  printf 'ipv6_clienthello_rows=%s\nipv4_control_capture=%s\n' "$v6_hellos" "$([[ -s "$run_dir/ipv4-control.pcap" ]] && echo present || echo absent)"
  printf 'scope=direct IPv6 egress versus same-host IPv4 control; this does not isolate CDN/path effects or establish a fingerprint cause\n'
} > "$run_dir/l6-status.txt"
find "$run_dir" -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > "$run_dir/SHA256SUMS"
printf 'L6 status: %s\nEvidence directory: %s\n' "$l6_status" "$run_dir"
[[ "$l6_status" == CAPTURED_REVIEW_REQUIRED ]]
