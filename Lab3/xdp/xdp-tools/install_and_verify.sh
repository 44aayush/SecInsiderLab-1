#!/usr/bin/env bash
# Install xdp-tools and run a few checks.  Run:  sudo ./install_and_verify.sh
# Safe to run again. Output is also written to logs/install_verify.log.
set -u
if [ "$(id -u)" -ne 0 ]; then echo "Run as root: sudo $0"; exit 1; fi
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HERE/logs"
exec > >(tee "$HERE/logs/install_verify.log") 2>&1

FAIL=0
run() { echo; echo "\$ $*"; "$@" || FAIL=1; }
# the tools print their usage and exit non-zero on 'help', so check the text instead
usage() { echo; echo "\$ $*"; "$@" 2>&1 | head -4; "$@" 2>&1 | grep -qi usage || FAIL=1; }

date; uname -r
echo; echo "=== install ==="
make -C "$HERE/xdp-tools" install >/dev/null && ldconfig && echo "installed to /usr/local/sbin" || FAIL=1
command -v xdp-loader xdp-filter xdpdump xdp-bench

echo; echo "=== checks ==="
usage xdp-loader help
usage xdp-filter help
usage xdpdump --help
run xdp-loader features lo
run xdp-loader status

echo
[ $FAIL -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $FAIL
