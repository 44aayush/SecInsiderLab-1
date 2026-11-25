#!/bin/bash
# Task 4 check: can the pinger container reach nginx and apache? PASS/FAIL per check, exit 1 on any FAIL.
# Run from anywhere; log is teed to outputs/task4/task4_check.log.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p outputs/task4
exec > >(tee outputs/task4/task4_check.log) 2>&1

fails=0
# check <label> <command...>: run inside pinger; print the captured output, then a PASS/FAIL line.
check() {
    local label=$1 out
    shift
    if out=$(docker compose exec -T pinger "$@" 2>&1); then
        echo "$out"
        echo "PASS: $label"
    else
        echo "$out"
        echo "FAIL: $label"
        fails=$((fails + 1))
    fi
}

docker compose ps

for target in nginx apache 172.28.2.10 172.28.2.11; do
    check "ping $target" ping -c 3 "$target"
done
# Capture first, then cut: "wget | head" would fail under pipefail when head closes the pipe early.
for target in nginx apache; do
    check "http $target (first 4 lines)" sh -c "wget -qO- http://$target | head -4"
done

if [ "$fails" -ne 0 ]; then
    echo "RESULT: $fails check(s) FAILED"
    exit 1
fi
echo "RESULT: all checks PASSED"
