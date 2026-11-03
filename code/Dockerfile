# Linux lab used for every capture and tool run in this project.
# Build:  docker build -t cn-lab -f code/Dockerfile code
# Real-world tools only: FoxIO ja4 (Rust) and Wireshark tshark (C).

# Step 1: build FoxIO's ja4 CLI
#   ja4      = pinned release tag (what people download today)
#   ja4-main = pinned unreleased commit on main (has the GREASE-in-signature-algorithms fix)
FROM rust:1-slim-trixie AS ja4build
ARG JA4_TAG=v0.18.6
ARG JA4_MAIN_COMMIT=c6469a7b0dbf8fe963810162429fbfd9d1acc4d5
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
 && cargo install --locked --git https://github.com/FoxIO-LLC/ja4 --tag ${JA4_TAG} ja4 \
 && cargo install --locked --git https://github.com/FoxIO-LLC/ja4 --rev ${JA4_MAIN_COMMIT} --root /ja4main ja4

# Step 2: the lab image
FROM debian:trixie-slim@sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      tshark tcpdump curl openssl ca-certificates chromium python3 python3-pytest \
      cmake g++ make libssl-dev ethtool iproute2 procps dnsutils \
 && rm -rf /var/lib/apt/lists/*
COPY --from=ja4build /usr/local/cargo/bin/ja4 /usr/local/bin/ja4
COPY --from=ja4build /ja4main/bin/ja4 /usr/local/bin/ja4-main
WORKDIR /lab
