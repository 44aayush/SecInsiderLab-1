#!/usr/bin/env bash
# Lab 4 end-to-end: train kernel models, test, build the XDP object and the IDS image, run the Docker stack.
# Needs Docker (no sudo: the user is in the docker group). Task 1 needs sudo and is printed at the end.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

QUICK=0
case "${1:-}" in
  "") ;;
  --quick) QUICK=1 ;;
  *) echo "usage: bash run.sh [--quick]" >&2; exit 2 ;;
esac
[ $# -le 1 ] || { echo "usage: bash run.sh [--quick]" >&2; exit 2; }

# Files written by the privileged container are chowned to this user (CLAUDE.md 9).
LAB4_UID=$(id -u)
LAB4_GID=$(id -g)
export LAB4_UID LAB4_GID

CSV=Friday-WorkingHours-Afternoon-DDos.csv
if [ ! -f "$CSV" ] || head -c 24 "$CSV" | grep -q '^version https://git-lfs'; then
  echo "$CSV is missing or a git-lfs pointer; run: git lfs pull" >&2
  exit 1
fi

echo "== 1/8 Environment"
[ -d .venv ] || uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

echo "== 2/8 Train the kernel models (DT + XGBoost), export, parity check"
if [ "$QUICK" = 1 ]; then
  MODELS=models_quick
  .venv/bin/python script/train.py --csv tests/fixtures/sample_ddos.csv --out outputs_quick --models-dir "$MODELS"
else
  MODELS=models
  .venv/bin/python script/train.py
fi

echo "== 3/8 Unit tests"
if [ "$QUICK" = 1 ]; then
  .venv/bin/pytest -m "not e2e and not kernel and not docker" -q
else
  .venv/bin/pytest -m "not kernel and not docker" -q
fi

echo "== 4/8 Build the XDP object (no root)"
make -C xdp

echo "== 5/8 Build the IDS image"
docker compose build ids

echo "== 6/8 Kernel tests (BPF_PROG_TEST_RUN inside the IDS image)"
docker run --rm --privileged -v "$PWD/$MODELS:/lab4/models:ro" lab4-ids:latest \
  python3 -m pytest tests/test_kernel.py -m kernel -q

echo "== 7/8 Docker stack, Task 4 check, 10 s agent run"
docker compose up -d
sleep 5
bash docker/task4_check.sh
docker compose exec -T ids python3 script/agent.py --iface ext0 --model ALL --timespan 10

echo "== 8/8 Done"
echo "Task 3 UI (host only): http://172.28.0.2:8080"
echo "Stop the stack: docker compose down"
echo "Task 1 needs sudo (see xdp_tools/README.md): sudo bash xdp_tools/task1_demo.sh 2>&1 | tee xdp_tools/logs/task1_demo.log"
