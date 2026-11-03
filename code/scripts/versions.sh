#!/bin/sh
# Record the lab toolchain with the output run; binaries are supplied by code/Dockerfile.
set -eu
printf 'date: %s\n' "$(date -u)"
printf 'kernel: %s\n' "$(uname -srm)"
printf 'ja4 (FoxIO release tag v0.18.6): %s\n' "$(ja4 --version)"
printf 'ja4-main (FoxIO commit c6469a7b0dbf8fe963810162429fbfd9d1acc4d5): %s\n' "$(ja4-main --version)"
printf 'tshark: %s\n' "$(tshark --version 2>/dev/null | head -1)"
printf 'tcpdump: %s\n' "$(tcpdump --version 2>&1 | head -1)"
printf 'curl: %s\n' "$(curl --version | head -1)"
printf 'openssl: %s\n' "$(openssl version)"
printf 'chromium: %s\n' "$(chromium --version)"
printf 'python: %s\n' "$(python3 --version)"
