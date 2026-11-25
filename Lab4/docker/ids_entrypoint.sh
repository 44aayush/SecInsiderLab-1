#!/bin/bash
# IDS container entrypoint: bpffs, NAT towards the back network, then run the command.
set -euo pipefail

mountpoint -q /sys/fs/bpf || mount -t bpf bpf /sys/fs/bpf

# Only in the compose topology; plain "docker run" (kernel tests) has no int0.
if ip link show int0 >/dev/null 2>&1; then
    iptables -t nat -C POSTROUTING -o int0 -j MASQUERADE 2>/dev/null \
        || iptables -t nat -A POSTROUTING -o int0 -j MASQUERADE
fi

exec "$@"
