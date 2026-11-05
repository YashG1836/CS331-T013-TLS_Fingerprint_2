# Track 1 results — audited import

These tool outputs and measurements are teammate-supplied from Yash's Docker lab; they were not rerun in this integration environment. The unmodified source summary is preserved at `results/imported/yash-summary.md` and `.json`. This audited view corrects the empty IPv6 capture: its zero-packet pcap cannot establish `tools_agree`. See `docs/track1-evidence-audit.md` for other provenance and interpretation limits.

## Imported Track 1 analysis table (audited copy; not regenerated in this checkout)

| id | limitation | hellos_tshark | hellos_ja4 | distinct_ja3 | distinct_ja4 | distinct_ja4_main | tools_agree | ja4x_ja4h_no_keys | ja4x_ja4h_with_keys | hello_bytes_max | pieces_max | biggest_frame | groups_chosen | ech_ext_hellos | seconds_tshark | seconds_ja4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| quic_chromium | L1 | 5 | 5 | 5 | 1 | 1 | True | 0 | - | 1887 | 21 | 1292 | [4588] | 5 | 0.069 | 0.125 |
| quic_curl | L1 | 5 | 5 | 1 | 1 | 1 | True | 0 | - | 1505 | 1 | 1242 | [4588] | 0 | 0.058 | 0.121 |
| tls_keylog_curl | L2 | 1 | 1 | 1 | 1 | 1 | True | 0 | 5 | 1566 | 1 | 1641 | [4588] | 0 | 0.057 | 0.113 |
| tls_offload_on | L3 | 3 | 3 | 1 | 1 | 1 | True | 0 | - | 1511 | 1 | 4913 | [4588] | 0 | 0.058 | 0.117 |
| tls_offload_off | L3 | 3 | 3 | 1 | 1 | 1 | True | 0 | - | 1511 | 2 | 2962 | [4588] | 0 | 0.056 | 0.118 |
| tls_pq_on | L4 | 5 | 5 | 1 | 1 | 1 | True | 0 | - | 1511 | 1 | 2962 | [4588] | 0 | 0.057 | 0.124 |
| tls_pq_off | L4 | 5 | 5 | 1 | 1 | 1 | True | 0 | - | 508 | 1 | 3825 | [29] | 0 | 0.057 | 0.123 |
| tls_chromium_repeat | L5 | 50 | 50 | 50 | 15 | 1 | True | 0 | - | 2016 | 1 | 5149 | [4588] | 50 | 0.062 | 0.211 |
| tls_curl_repeat | L5 | 10 | 10 | 1 | 1 | 1 | True | 0 | - | 1569 | 1 | 4913 | [4588] | 0 | 0.057 | 0.141 |
| tls_python_repeat | L5 | 10 | 10 | 1 | 1 | 1 | True | 0 | - | 1570 | 1 | 4919 | [4588] | 0 | 0.058 | 0.13 |
| tls_ipv4 | L6 | 3 | 3 | 1 | 1 | 1 | True | 0 | - | 1569 | 1 | 4911 | [4588] | 0 | 0.057 | 0.119 |
| tls_ipv6 | L6 | 0 | 0 | 0 | 0 | 0 | not comparable | 0 | - | 0 | — | 0 | [] | 0 | 0.058 | 0.111 |
| tls_ech_off | L7 | 5 | 5 | 5 | 4 | 1 | True | 0 | - | 1730 | 1 | 5148 | [4588] | 0 | 0.057 | 0.121 |
| tls_ech_on | L7 | 5 | 5 | 5 | 4 | 1 | True | 0 | - | 2014 | 1 | 2743 | [4588] | 5 | 0.057 | 0.122 |
| tls_ech_doh | L7 | 12 | 12 | 12 | 9 | 1 | True | 0 | - | 2013 | 1 | 2512 | [29, 4588] | 12 | 0.058 | 0.126 |
