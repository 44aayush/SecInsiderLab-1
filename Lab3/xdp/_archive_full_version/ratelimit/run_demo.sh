#!/usr/bin/env bash
# run_demo.sh - end-to-end demo of the XDP per-source-IP rate limiter.
#
#   sudo ./run_demo.sh                 # defaults: 100 pps limit, 5 s flood
#   sudo PPS=50 FLOOD_SECS=8 ./run_demo.sh
#   sudo ATTACK="-i u200" ./run_demo.sh   # 5000 pps instead of --flood
#
# Topology (all in throw-away network namespaces, host is not touched):
#
#   rl-attacker 10.10.0.2 --att0==+                       +==vic0  rl-victim 10.10.0.1
#                                  |  rl-lan: bridge br0  |        ^ XDP rate limiter
#   rl-benign   10.10.0.3 --ben0==+                       |          attached here
#
# Everything is printed with timestamps and also written to logs/demo.log.
set -uo pipefail

PPS=${PPS:-100}
FLOOD_SECS=${FLOOD_SECS:-5}
ATTACK=${ATTACK:---flood}
VICTIM_IP=10.10.0.1
ATTACKER_IP=10.10.0.2
BENIGN_IP=10.10.0.3
NS_V=rl-victim NS_L=rl-lan NS_A=rl-attacker NS_B=rl-benign
IFACE=vic0

cd "$(dirname "$(readlink -f "$0")")"
[ "$(id -u)" -eq 0 ] || { echo "run as root: sudo $0"; exit 1; }
for t in ip bpftool hping3 ping timeout awk; do
	command -v "$t" >/dev/null || { echo "missing tool: $t"; exit 1; }
done
[ -x ./xdp_ratelimit_user ] && [ -f ./xdp_ratelimit.bpf.o ] || { echo "run 'make' first"; exit 1; }

mkdir -p logs
LOG=logs/demo.log
: > "$LOG"
# timestamp every line, show it on the terminal and append it to the log
exec > >(trap '' INT TERM; while IFS= read -r l; do printf '%(%H:%M:%S)T  %s\n' -1 "$l"; done | tee -a "$LOG") 2>&1

LOADER_PID=""
phase() { echo; echo "=================================================================="; \
          echo "  PHASE $1"; echo "=================================================================="; }
run()   { echo "\$ $*"; "$@"; }
inv()   { ip netns exec "$@"; }

stop_loader() {
	if [ -n "$LOADER_PID" ] && kill -0 "$LOADER_PID" 2>/dev/null; then
		# LOADER_PID is the backgrounded subshell (ignores SIGINT); signal the loader itself
		pkill -TERM -P "$LOADER_PID" 2>/dev/null; kill -TERM "$LOADER_PID" 2>/dev/null
		wait "$LOADER_PID" 2>/dev/null
	fi
	LOADER_PID=""
}

cleanup() {
	trap - EXIT INT TERM
	echo; echo "--- cleanup: stopping loader, detaching XDP, deleting namespaces ---"
	stop_loader
	ip -n $NS_V link set dev $IFACE xdp off 2>/dev/null
	for ns in $NS_A $NS_B $NS_V $NS_L; do ip netns del $ns 2>/dev/null; done
	[ -n "${SUDO_USER:-}" ] && chown -R "$SUDO_USER": logs 2>/dev/null
	echo "--- cleanup done; log: $(pwd)/$LOG ---"
	sleep 0.3
}
trap cleanup EXIT
trap 'exit 130' INT TERM

# start the libbpf loader in the victim namespace, wait until it has attached
start_loader() { # $1 = mode, $2 = log file
	inv $NS_V ./xdp_ratelimit_user $IFACE --pps "$PPS" --mode "$1" --top 4 > "$2" 2>&1 &
	LOADER_PID=$!
	for _ in $(seq 50); do
		grep -q '^attached' "$2" && { cat "$2"; return 0; }
		kill -0 $LOADER_PID 2>/dev/null || break
		sleep 0.2
	done
	cat "$2"; LOADER_PID=""; return 1
}

# TcpInSegs of the victim namespace (/proc/net/snmp is per network namespace)
tcp_insegs() {
	inv $NS_V awk '/^Tcp:/ { if (h) { print $c; exit } h = 1; for (i = 1; i <= NF; i++) if ($i == "InSegs") c = i }' /proc/net/snmp
}

# flood from attacker while benign client pings; count what reaches the stack
attack_round() { # $1 = tag
	local secs=$FLOOD_SECS
	echo "--- attacker $ATTACKER_IP: hping3 -S -p 80 $ATTACK for ${secs}s;" \
	     "benign $BENIGN_IP: ping -i 0.2 in parallel ---"
	# Count TCP segments that reach the victim's IP stack (i.e. passed XDP) with the
	# kernel's own SNMP counter in the victim netns. (tcpdump was used before, but it
	# hangs after SIGTERM when no further matching packet arrives to wake it up.)
	local in0 in1
	in0=$(tcp_insegs)
	inv $NS_B ping -c $((secs * 5)) -i 0.2 -W 1 $VICTIM_IP > "logs/benign_$1.log" 2>&1 &
	local pingp=$!
	inv $NS_A timeout -s INT "$secs" hping3 -S -p 80 $ATTACK $VICTIM_IP > "logs/hping3_$1.log" 2>&1
	wait $pingp
	sleep 0.5
	in1=$(tcp_insegs)
	echo "[attacker] $(grep -E 'packets transmitted' "logs/hping3_$1.log")"
	echo "[victim  ] TCP segments that reached the victim stack (passed XDP): $((in1 - in0))" \
	     | tee "logs/victim_$1.log"
	echo "[benign  ] $(grep -E 'packets transmitted' "logs/benign_$1.log")"
}

le64() { local v=$1 i; for i in 0 1 2 3 4 5 6 7; do printf '%02x ' $(( (v >> (8 * i)) & 255 )); done; }
# print only the non-zero per-CPU slots of the rl_stats map
percpu_dump() {
	bpftool map dump id "$1" | awk '
		/"key"/   { k = $0; gsub(/[^0-9]/, "", k) }
		/"cpu"/   { c = $0; gsub(/[^0-9]/, "", c) }
		/"value"/ { v = $0; gsub(/[^0-9]/, "", v)
		            if (v + 0 > 0) printf "  stat %s (%s)  cpu %-3s %s\n", k, n[k], c, v }
		BEGIN { n[0]="pass"; n[1]="drop-rate"; n[2]="drop-block"; n[3]="non-IPv4" }'
}
map_id() { bpftool map show name "$1" 2>/dev/null | awk -F: 'NR==1 {print $1}'; }

#########################################################################
phase "0 - build lab topology (4 network namespaces, veth pairs, bridge)"
for ns in $NS_A $NS_B $NS_V $NS_L; do ip netns del $ns 2>/dev/null; ip netns add $ns; done
ip -n $NS_L link add br0 type bridge forward_delay 0
ip link add $IFACE netns $NS_V type veth peer name l-vic netns $NS_L
ip link add att0   netns $NS_A type veth peer name l-att netns $NS_L
ip link add ben0   netns $NS_B type veth peer name l-ben netns $NS_L
for p in l-vic l-att l-ben; do ip -n $NS_L link set $p master br0 up; done
ip -n $NS_L link set br0 up
ip -n $NS_V addr add $VICTIM_IP/24   dev $IFACE; ip -n $NS_V link set $IFACE up
ip -n $NS_A addr add $ATTACKER_IP/24 dev att0;   ip -n $NS_A link set att0 up
ip -n $NS_B addr add $BENIGN_IP/24   dev ben0;   ip -n $NS_B link set ben0 up
for ns in $NS_A $NS_B $NS_V $NS_L; do ip -n $ns link set lo up; done
run ip netns list
run ip -n $NS_V -br addr show dev $IFACE
inv $NS_A ping -c 2 -W 1 $VICTIM_IP >/dev/null && inv $NS_B ping -c 2 -W 1 $VICTIM_IP >/dev/null \
	&& echo "connectivity OK (attacker->victim, benign->victim)" || echo "WARNING: no connectivity"

#########################################################################
phase "1 - BASELINE without XDP: attacker flood reaches the victim stack"
attack_round baseline

#########################################################################
phase "2 - attach xdp_ratelimit in GENERIC (skb) mode, limit = $PPS pkt/s per source IP"
start_loader skb logs/loader_skb.log || { echo "loader failed"; exit 1; }
run ip -n $NS_V link show dev $IFACE
run bpftool prog show name xdp_ratelimit
run bpftool net show   # (only shows root-netns devices; vic0 lives in $NS_V)
inv $NS_V bpftool net show dev $IFACE

#########################################################################
phase "3 - benign client alone (5 pkt/s < $PPS) -> nothing dropped"
run inv $NS_B ping -c 15 -i 0.2 -W 1 $VICTIM_IP | tail -n 3

#########################################################################
phase "4 - ATTACK with XDP rate limiter (generic mode): flood dropped, benign survives"
attack_round xdp_skb
echo "--- loader output (last seconds) ---"
tail -n 18 logs/loader_skb.log

#########################################################################
phase "5 - inspect BPF maps with bpftool"
run bpftool map show name rl_state
echo "\$ bpftool map dump name rl_stats   (per-CPU array; only non-zero CPU slots shown)"
percpu_dump "$(map_id rl_stats)"
run bpftool map dump name rl_state
run bpftool map dump name rl_config

#########################################################################
phase "6 - runtime control from user space (no recompile, no reload)"
CFG=$(map_id rl_config)
BLK=$(map_id rl_block)
echo "6a) raise limit to 1000 pkt/s via 'bpftool map update' (rl_config id $CFG)"
run bpftool map update id "$CFG" key 0 0 0 0 value hex $(le64 1000) $(le64 1000000000)
run bpftool map dump id "$CFG"
sleep 2; tail -n 6 logs/loader_skb.log
echo "6b) restore limit $PPS, then put attacker $ATTACKER_IP on the BLOCK-list (rl_block id $BLK)"
echo "    (this is the hook an IDS / the Lab 3 ML model would use)"
run bpftool map update id "$CFG" key 0 0 0 0 value hex $(le64 "$PPS") $(le64 1000000000)
run bpftool map update id "$BLK" key ${ATTACKER_IP//./ } value 1
echo "attacker pings victim (expect 100% loss):"
inv $NS_A ping -c 5 -i 0.2 -W 1 $VICTIM_IP | grep 'packets transmitted'
echo "benign pings victim (expect 0% loss):"
inv $NS_B ping -c 5 -i 0.2 -W 1 $VICTIM_IP | grep 'packets transmitted'
sleep 1; tail -n 6 logs/loader_skb.log
stop_loader
echo "loader stopped -> program detached:"
run ip -n $NS_V link show dev $IFACE

#########################################################################
phase "7 - same program in NATIVE (driver) mode - veth supports native XDP"
if start_loader native logs/loader_native.log; then
	run ip -n $NS_V link show dev $IFACE
	attack_round xdp_native
	echo "--- loader output (last seconds) ---"
	tail -n 12 logs/loader_native.log
	stop_loader
else
	echo "native attach failed on this kernel/driver - see logs/loader_native.log"
fi

#########################################################################
phase "8 - alternative loading path: iproute2 + bpftool only (no custom loader)"
run ip -n $NS_V link set dev $IFACE xdpgeneric obj xdp_ratelimit.bpf.o sec xdp
run ip -n $NS_V link show dev $IFACE
CFG=$(map_id rl_config)
echo "config map is all-zero after 'ip' load => limiter disabled; enable it with bpftool:"
run bpftool map update id "$CFG" key 0 0 0 0 value hex $(le64 "$PPS") $(le64 1000000000)
FLOOD_SECS=3 attack_round xdp_iproute2
echo "\$ bpftool map dump name rl_stats   (per-CPU array; only non-zero CPU slots shown)"
percpu_dump "$(map_id rl_stats)"
run ip -n $NS_V link set dev $IFACE xdpgeneric off

phase "DONE - see logs/ for raw hping3 / tcpdump / ping / loader output"
