# Track 1 capture-log context

The imported capture log came from Yash's Docker lab on macOS/aarch64, with `tcpdump` on container `eth0`. It reports packet totals for the saved pcap files and shows the manifest client command repeated according to each row's `repeat` value. The original absolute workstation path has been omitted. Full capture commands, filters, setup commands, and repeat counts are retained per capture in `captures/manifest.json` and `captures/metadata/<capture_id>.json`.

The log contains no per-invocation client exit status and does not establish that each repeated request succeeded. For the IPv6 case it reports zero packets, consistent with the 24-byte empty `tls_ipv6.pcap`. The log also records Docker Desktop as the capture vantage, so observed segmentation and SYN values must not be described as a physical-wire measurement.
