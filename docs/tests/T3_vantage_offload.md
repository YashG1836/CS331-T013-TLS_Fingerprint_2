# T3: Does where and how we capture change what we see? (L3)

**One line:** capture the *same* ClientHello with the kernel's segmentation offload on and then off, and compare what the capture shows.

## What is being done
- Link MTU set to **1500** (a normal internet size).
- curl sends a large post-quantum ClientHello (bigger than one packet), **3 times** with TSO/GSO **on**, **3 times** with TSO/GSO **off** (`ethtool -K eth0 tso off gso off`).
- We also read the TCP SYN / SYN-ACK values the capture shows.

## What is being tested
1. In how many packets does the ClientHello appear, and how big are they?
2. Does JA4 change?
3. Are the TCP values we see really the server's?

## Why
- Sir (about the other group): *"enable certain optimisations like GRO, LSO… just changing one parameter in the network stack can affect completely the way you have to fingerprint."*
- TSO/GSO: the kernel hands **one big packet** to the network card and lets it cut the packet up later. A capture taken before that sees a packet that never exists on the wire.
- TCP fingerprints (JA4T, JA4TS) use SYN values like MSS (RFC 9293 §3.7.1). They describe **whichever TCP stack is next to the tap**: a proxy that ends TCP and opens a new connection replaces them; a NAT only rewrites addresses and lowers TTL.

## Control / what stays the same
Same client, same hello, same server, same MTU. Only the offload switch changes.

## Commands
```sh
make lab-capture CAPTURE_ID=tls_offload_on
make lab-capture CAPTURE_ID=tls_offload_off
make lab-eval                    # column pieces_max
tshark -r captures/pcaps/tls_offload_on.pcap -Y "tcp.flags.syn==1" -T fields -e ip.src -e tcp.options.mss_val -e ip.ttl
```

## Expected
Offload on → 1 oversized frame; off → 2 normal frames; JA4 the same.

## What we saw
Re-checked from the pcaps with TShark ([`results/track1/recheck-20261106.md`](../../results/track1/recheck-20261106.md)):

| | ClientHello as captured | JA4 |
|---|---|---|
| offload on | **1 frame of 1586 bytes**, bigger than the 1500 MTU | `t13d3012h2_1d37bd780c83_7f037f8d6676` |
| offload off | **2 frames: 1514 + 138 bytes** | same |

(`summary.md` column `biggest_frame` is the biggest frame of the whole pcap in any direction, so it shows 4913 / 2962.)

SYN values in the same capture:

| packet | MSS | TTL | window scale |
|---|---|---|---|
| our SYN | 1460 | 64 | 10 |
| "Cloudflare's" SYN-ACK | **65495** | 63 | 7 |

An MSS of 65495 cannot come over a 1500-byte path. It comes from **Docker Desktop's network proxy**, which answers the TCP handshake itself. It is not Cloudflare. Offload does not change MSS; it only changes how the hello is cut in the capture.

A second run on Windows (Miloni, `results/l3_paired_batch/`) captured the same kind of request inside the container and on the Wi-Fi card at the same time:

| where | client SYN: TTL / window / wscale / MSS / timestamps |
|---|---|
| inside the container | 64 / 64240 / 10 / 1460 / yes (Linux) |
| on the Wi-Fi card | 128 / 65535 / 8 / 1460 / no (Windows) |

The container's connection leaves the laptop as a **new TCP connection made by Windows** (different ISN, Windows defaults). For comparison, traffic from a Linux VM on the `vEthernet (WSL)` adapter keeps its Linux values and its ISN on the Wi-Fi (only TTL 64 -> 63), i.e. normal NAT.

## What it means
- TLS-level fingerprints (JA4) survive. Packet-level views (sizes, counts) depend on capture settings.
- TCP-level fingerprints (JA4T, JA4TS) describe the **nearest TCP stack**. Here JA4TS would describe Docker's proxy, and on the Wi-Fi JA4T would describe Windows, not the Linux container. A NAT keeps them; a proxy replaces them.

## What it does NOT prove
- The Mac run has one vantage point (inside the container). The Windows run adds the Wi-Fi card, but only 3 requests.
- JA4T was not in our pinned tools (TShark 4.4.19, FoxIO v0.18.6). FoxIO v1.0.1 has it; on `tls_offload_on` it gives `64240_2-4-8-1-3_1460_10` (the container's SYN).
