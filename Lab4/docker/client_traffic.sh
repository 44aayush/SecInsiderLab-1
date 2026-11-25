#!/bin/sh
# Normal-traffic client (CLAUDE.md 5.6): route the back network via the IDS gateway, then GET both servers forever.
# Logs one line per request: <ISO time> <server> OK|FAIL (visible in "docker compose logs client").
set -eu

ip route add 172.28.2.0/24 via 172.28.1.2

while true; do
    for server in 172.28.2.10 172.28.2.11; do
        if wget -q -T 3 -O /dev/null "http://$server/"; then status=OK; else status=FAIL; fi
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $server $status"
    done
    sleep "${CLIENT_INTERVAL_S:-1}"
done
