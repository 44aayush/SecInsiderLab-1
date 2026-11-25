#!/usr/bin/env bash
# Lab 3 end-to-end: train/compare models, run tests, build the XDP programs (no root).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

QUICK=0
case "${1:-}" in
  "") ;;
  --quick) QUICK=1 ;;
  *) echo "usage: bash run.sh [--quick]" >&2; exit 2 ;;
esac
[ $# -le 1 ] || { echo "usage: bash run.sh [--quick]" >&2; exit 2; }

CSV=Friday-WorkingHours-Afternoon-DDos.csv
if [ ! -f "$CSV" ] || head -c 24 "$CSV" | grep -q '^version https://git-lfs'; then
  echo "$CSV is missing or a git-lfs pointer; run: git lfs pull" >&2
  exit 1
fi

echo "== 1/5 Environment"
[ -d .venv ] || uv venv
uv pip install -r requirements.txt --torch-backend=cpu

echo "== 2/5 Train and compare models (Tasks 1-3)"
if [ "$QUICK" = 1 ]; then
  .venv/bin/python script/main.py --epochs 1 --out outputs_quick
else
  .venv/bin/python script/main.py
fi

echo "== 3/5 Tests"
if [ "$QUICK" = 1 ]; then
  .venv/bin/python -m pytest -m "not e2e" -q
else
  .venv/bin/python -m pytest -q
fi

echo "== 4/5 Build XDP programs (Tasks 4-5, no root)"
if command -v clang >/dev/null 2>&1; then
  make -C xdp
  make -C xdp/ratelimit
else
  echo "clang not found: skipping the XDP build"
fi

echo "== 5/5 Done"
echo "The XDP attach/block/stats demo needs sudo; see xdp/README.md and xdp/ratelimit/README.md."
