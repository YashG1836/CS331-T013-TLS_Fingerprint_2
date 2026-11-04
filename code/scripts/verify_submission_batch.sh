#!/usr/bin/env bash
# Batch the repeatable WSL checks into one run and preserve outputs in tracked results/track2/.
set -euo pipefail

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  cat <<'USAGE'
Usage: code/scripts/verify_submission_batch.sh [results/track2/RUN_DIRECTORY]

Runs manifest checks, make test, preflight, QUIC DCID inventory, imported offload
SYN analysis, and both deterministic QUIC impairment comparisons. All outputs are
written under a new tracked results/track2 directory. It does not perform a live
capture or a Windows-side capture. Review privacy and output before committing.
USAGE
  exit 0
fi

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"
run_dir=${1:-"results/track2/verification-batch-$(date +%Y%m%d-%H%M%S)"}
case "$run_dir" in
  results/track2/*) ;;
  *) echo "output must be under results/track2/: $run_dir" >&2; exit 2 ;;
esac
if [[ -e "$run_dir" ]]; then
  echo "output directory already exists: $run_dir" >&2
  exit 2
fi
if ! command -v tshark >/dev/null 2>&1; then
  echo "tshark not found on PATH" >&2
  exit 2
fi

mkdir -p "$run_dir"
{
  printf 'timestamp=%s\n' "$(date --iso-8601=seconds)"
  printf 'commit=%s\n' "$(git rev-parse HEAD)"
  printf 'branch=%s\n' "$(git branch --show-current)"
  printf '\n-- tool versions --\n'
  python3 --version
  tshark --version
  g++ --version
  openssl version
} > "$run_dir/environment.txt" 2>&1

sha256sum \
  captures/pcaps/quic_chromium.pcap \
  captures/pcaps/quic_curl.pcap \
  captures/pcaps/tls_offload_on.pcap \
  captures/pcaps/tls_offload_off.pcap \
  > "$run_dir/input-capture-sha256.txt"
sha256sum \
  code/scripts/verify_submission_batch.sh \
  code/scripts/quic_impairment.py \
  code/scripts/quic_initial_inventory.py \
  code/scripts/l3_proxy_sanity.py \
  > "$run_dir/script-sha256.txt"

python3 code/scripts/preflight.py --output "$run_dir/preflight.json" \
  > "$run_dir/preflight.log" 2>&1
make check 2>&1 | tee "$run_dir/manifest-check.log"
make test 2>&1 | tee "$run_dir/make-test.log"

python3 code/scripts/quic_initial_inventory.py \
  --input captures/pcaps/quic_chromium.pcap \
  --input captures/pcaps/quic_curl.pcap \
  --output "$run_dir/quic-initial-dcid-inventory.json"

python3 code/scripts/l3_proxy_sanity.py \
  --capture offload_on=captures/pcaps/tls_offload_on.pcap \
  --capture offload_off=captures/pcaps/tls_offload_off.pcap \
  --tshark tshark \
  --output "$run_dir/offload-syn-analysis.json" \
  2>&1 | tee "$run_dir/offload-syn-analysis.log"

python3 code/scripts/quic_impairment.py \
  --input captures/pcaps/quic_chromium.pcap \
  --work-dir "$run_dir/quic-impairment/chromium" \
  --extractor build/code/quic/src/quic-fingerprint --tshark tshark --seed 331 \
  2>&1 | tee "$run_dir/quic-chromium-impairment.log"

python3 code/scripts/quic_impairment.py \
  --input captures/pcaps/quic_curl.pcap \
  --work-dir "$run_dir/quic-impairment/curl" \
  --extractor build/code/quic/src/quic-fingerprint --tshark tshark --seed 331 \
  2>&1 | tee "$run_dir/quic-curl-impairment.log"

find "$run_dir" -type f ! -name SHA256SUMS -print0 \
  | sort -z | xargs -0 sha256sum > "$run_dir/SHA256SUMS"
printf '\nBatch completed: %s\nReview privacy and results before committing this directory.\n' "$run_dir"
