#!/usr/bin/env bash
# Install xdp-tools and verify it. Run:  sudo ./install_and_verify.sh
# Idempotent; the temporary namespace/veth are removed on exit (trap).
# Env: SKIP_INSTALL=1 uses binaries in place instead of "make install".
set -u
if [ "$(id -u)" -ne 0 ]; then echo "Run as root: sudo $0"; exit 1; fi
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/xdp-tools"
mkdir -p "$HERE/logs"
LOG="$HERE/logs/install_verify.log"
exec > >(tee "$LOG") 2>&1

NS=xdpt-ns; VH=xdpt-h; VN=xdpt-n
HOST_IP=10.77.0.1; NS_IP=10.77.0.2
FAIL=0
step() { echo; echo "=== $* ==="; }
chk()  { # chk "desc" cmd...
  local d="$1"; shift
  echo "+ $*"
  if "$@"; then echo "[PASS] $d"; else echo "[FAIL] $d"; FAIL=1; fi
}

cleanup() {
  set +e
  echo; echo "=== cleanup ==="
  [ -n "${XF:-}" ] && $XF unload $VH >/dev/null 2>&1
  ip netns del $NS 2>/dev/null
  ip link del $VH 2>/dev/null
  echo "namespace and veth removed"
}
trap cleanup EXIT
cleanup >/dev/null 2>&1   # clear leftovers from earlier runs

date; uname -r

step "Install"
if [ "${SKIP_INSTALL:-0}" = 1 ]; then
  echo "SKIP_INSTALL=1: using binaries in place"
  XL=$SRC/xdp-loader/xdp-loader; XF=$SRC/xdp-filter/xdp-filter
  XD=$SRC/xdp-dump/xdpdump;      XB=$SRC/xdp-bench/xdp-bench
  export LD_LIBRARY_PATH="$SRC/lib/libxdp${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
else
  chk "make install" make -C "$SRC" install
  ldconfig
  XL=xdp-loader; XF=xdp-filter; XD=xdpdump; XB=xdp-bench
fi
echo "using: $(command -v $XL || echo $XL)"

step "Tool smoke tests"
echo "NOTE: this xdp-loader has no --version option (it prints 'Command --version is unknown'); using 'help' + version.mk"
$XL --version 2>&1 | head -1 || true
grep -E 'TOOLS_VERSION|LIBXDP_VERSION' "$SRC/version.mk" 2>/dev/null || true
# these tools print usage and exit non-zero on help, so check the output text instead
helpchk() { local d="$1"; shift; echo "+ $*"; if "$@" 2>&1 | tee /dev/stderr | grep -qi usage; then echo "[PASS] $d"; else echo "[FAIL] $d"; FAIL=1; fi; }
helpchk "xdp-loader help"  $XL help
helpchk "xdp-filter help"  $XF help
helpchk "xdpdump --help"   $XD --help
helpchk "xdp-bench help"   $XB help

step "Loopback"
chk "xdp-loader features lo" $XL features lo
chk "xdp-loader status"      $XL status

step "Functional test: xdp-filter on veth in netns (skb/generic mode)"
ip netns add $NS
ip link add $VH type veth peer name $VN
ip link set $VN netns $NS
ip addr add $HOST_IP/24 dev $VH; ip link set $VH up
ip netns exec $NS ip addr add $NS_IP/24 dev $VN
ip netns exec $NS ip link set $VN up
ip netns exec $NS ip link set lo up
chk "baseline ping works" ping -c2 -W1 $NS_IP

# Attach on the HOST-side veth (root netns): 'ip netns exec' remounts /sys, which hides
# the bpffs (/sys/fs/bpf) that xdp-filter needs for its pinned maps.
# Traffic from the namespace (src $NS_IP) arrives on $VH, so we drop that source.
chk "xdp-filter load (skb mode) on $VH" $XF load -m skb $VH
chk "add drop rule for src $NS_IP" $XF ip -m src $NS_IP
$XF status
echo "+ ping from namespace (expected to FAIL while rule active)"
if ip netns exec $NS ping -c3 -W1 $HOST_IP; then echo "[FAIL] ping still works with drop rule"; FAIL=1
else echo "[PASS] ping blocked by xdp-filter"; fi
echo "+ xdp-filter poll (statistics, 3s)"
timeout 3 $XF poll || true
chk "remove rule" $XF ip -r -m src $NS_IP
chk "ping works again after rule removal" ip netns exec $NS ping -c3 -W1 $HOST_IP
chk "xdp-filter status" $XF status
chk "xdp-filter unload" $XF unload $VH
$XL status || true

step "Result"
if [ $FAIL -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECKS FAILED (see [FAIL] lines)"; fi
exit $FAIL
