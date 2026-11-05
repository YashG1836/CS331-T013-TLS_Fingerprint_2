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
- TCP fingerprints (JA4T, JA4TS) use SYN values like MSS (RFC 9293 §3.7.1). They describe **whichever TCP stack is next to the tap**: a proxy or NAT that ends TCP replaces them.

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
The committed aggregate summary reports:

| | ClientHello length max | `pieces_max` | largest frame in the whole pcap | JA4 |
|---|---:|---:|---:|---|
| offload on | 1511 bytes | 1 | 4913 bytes | `t13d3012h2_1d37bd780c83_7f037f8d6676` |
| offload off | 1511 bytes | 2 | 2962 bytes | same |

The original test narrative separately reports a 1586-byte frame and a `1514 + 138` split, but those values do not match the saved aggregate fields and are not represented in the imported raw analysis JSON. They need a targeted rerun before being quoted. The narrative also reports a SYN-ACK MSS of 65495 (TTL 63) versus a client MSS of 1460 (TTL 64), interpreted as Docker Desktop proxy behavior. That observation is team-reported; the analyzer's saved raw JSON does not preserve the SYN field rows needed to independently verify the claim. The captures are inside Docker, not on the physical wire.

## What it means
- TLS-level fingerprints (JA4) survive. Packet-level views (sizes, counts) depend on capture settings.
- TCP-level fingerprints taken behind a proxy/NAT fingerprint **the proxy**. A JA4TS here would describe Docker.

## What it does NOT prove
- Only one vantage point (inside the container). A real tap on the wire would be the next step.
- We couldn't compute JA4T itself: neither tool supports it (see T0).
