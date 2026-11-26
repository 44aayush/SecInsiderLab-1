#!/usr/bin/env bash
# Task 1 demo: xdp-filter and xdpdump example commands (README.org forms) in a netns/veth sandbox.
# Never touches a real interface. Usage: sudo bash xdp_tools/task1_demo.sh 2>&1 | tee xdp_tools/logs/task1_demo.log
set -euo pipefail

NS=lab4t1
HOST_IF=t1-host
NS_IF=t1-ns
HOST_IP=10.10.0.1
NS_IP=10.10.0.2
HTTP_PORT=8000
HTTP_PID=""

if [[ $EUID -ne 0 ]]; then
    echo "Run as root: sudo $0" >&2
    exit 1
fi
for tool in xdp-filter xdpdump ip tcpdump python3; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool (install xdp-tools first, see xdp_tools/README.md)" >&2; exit 1; }
done

cleanup() {
    set +e
    echo "== cleanup =="
    xdp-filter unload "$HOST_IF" >/dev/null 2>&1
    [[ -n "$HTTP_PID" ]] && kill "$HTTP_PID" 2>/dev/null
    ip netns del "$NS" 2>/dev/null
    ip link del "$HOST_IF" 2>/dev/null
}
trap cleanup EXIT

banner() { printf '\n== %s ==\n' "$*"; }
# Echo the command, then run it; a failure aborts the script.
run() { echo "+ $*"; "$@"; }
# Echo the command, then run it; a failure is reported but tolerated ("expected to fail" steps, timeouts).
try() { echo "+ $*"; "$@" || echo "(exit status $? -- tolerated)"; }
in_ns() { ip netns exec "$NS" "$@"; }
# Start a 1 Hz ping from the netns in the background (traffic for the capture sections).
bg_ping() { in_ns ping -c "$1" -i 1 "$HOST_IP" >/dev/null 2>&1 & PING_PID=$!; }
# Runs on the host against the server inside the netns; exit 0 only on HTTP 200, "timeout" instead of a traceback.
http_get() {
    python3 -c "
import sys, urllib.request as u
try:
    s = u.urlopen('http://$NS_IP:$HTTP_PORT/', timeout=3).status
    print(s)
    sys.exit(0 if s == 200 else 1)
except Exception:
    print('timeout')
    sys.exit(1)
"
}

# Sandbox: stale leftovers first, then netns + veth pair.
ip netns del "$NS" 2>/dev/null || true
ip link del "$HOST_IF" 2>/dev/null || true
run ip netns add "$NS"
run ip link add "$HOST_IF" type veth peer name "$NS_IF"
run ip link set "$NS_IF" netns "$NS"
run ip addr add "$HOST_IP/24" dev "$HOST_IF"
run ip link set "$HOST_IF" up
run ip netns exec "$NS" ip addr add "$NS_IP/24" dev "$NS_IF"
run ip netns exec "$NS" ip link set "$NS_IF" up
run ip netns exec "$NS" ip link set lo up

banner "1. xdpdump -D (nothing loaded)"
try xdpdump -D

banner "2. xdp-filter load --mode skb $HOST_IF, then xdpdump -D"
run xdp-filter load --mode skb "$HOST_IF"
try xdpdump -D

banner "3. ping from the netns (0% loss)"
run in_ns ping -c 3 "$HOST_IP"

banner "4. block source $NS_IP, ping again (expected to fail), xdp-filter status"
run xdp-filter ip "$NS_IP" -m src
try in_ns ping -c 3 -W 1 "$HOST_IP"
run xdp-filter status

banner "5. xdpdump entry,exit while pinging (exit action XDP_DROP), then remove the rule"
bg_ping 6
try timeout 8 xdpdump -i "$HOST_IF" --rx-capture=entry,exit
wait "$PING_PID" 2>/dev/null || true
run xdp-filter ip "$NS_IP" -m src -r
run in_ns ping -c 3 "$HOST_IP"

banner "6. port filter on TCP $HTTP_PORT"
# Server inside the netns: the host's ufw drops inbound TCP SYNs on the host side.
in_ns python3 -m http.server "$HTTP_PORT" --bind "$NS_IP" >/dev/null 2>&1 &
HTTP_PID=$!
for _ in $(seq 10); do http_get >/dev/null 2>&1 && break; sleep 0.5; done
run http_get
run xdp-filter port "$HTTP_PORT" -m src
try http_get
run xdp-filter status
run xdp-filter port "$HTTP_PORT" -m src -r
run http_get
kill "$HTTP_PID" 2>/dev/null || true; wait "$HTTP_PID" 2>/dev/null || true; HTTP_PID=

banner "7. xdpdump -x (hex dump) while pinging"
bg_ping 5
try timeout 6 xdpdump -i "$HOST_IF" -x
wait "$PING_PID" 2>/dev/null || true

banner "8. xdpdump -w - | tcpdump -r - -n while pinging"
bg_ping 5
echo "+ timeout 6 xdpdump -i $HOST_IF -w - | tcpdump -r - -n"
timeout 6 xdpdump -i "$HOST_IF" -w - | tcpdump -r - -n || echo "(exit status $? -- tolerated)"
wait "$PING_PID" 2>/dev/null || true

banner "9. xdp-filter poll -i 1000 (5 s)"
bg_ping 5
try timeout -s INT 5 stdbuf -oL xdp-filter poll -i 1000
wait "$PING_PID" 2>/dev/null || true

banner "10. xdp-filter unload, then xdpdump -D (nothing loaded)"
run xdp-filter unload "$HOST_IF"
try xdpdump -D
