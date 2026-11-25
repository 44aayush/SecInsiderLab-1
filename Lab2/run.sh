#!/usr/bin/env bash
# One-shot reproduction of Lab 2 (Tasks 3 and 4, Friday DDoS). Regenerates artifacts/, outputs/ and report/tables/.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

for f in Friday-WorkingHours-Afternoon-DDos.csv task2_lab2.pcap_Flow.csv; do
  if [[ ! -f "$f" ]] || head -c 24 "$f" | grep -q '^version https://git-lfs'; then
    echo "ERROR: $f is missing or a git-lfs pointer. run: git lfs pull" >&2
    exit 1
  fi
done

echo "== uv sync =="
uv sync
echo "== Task 3: pre-processing =="
uv run python scripts/task3_preprocess.py
echo "== Task 4: training and evaluation =="
uv run python scripts/task4_train.py
echo "== Real-time detection on task2_lab2.pcap_Flow.csv =="
uv run python scripts/realtime_detect.py task2_lab2.pcap_Flow.csv
echo "== Report tables (writes report/tables/*.tex) =="
uv run python scripts/make_report_tables.py
echo "== Tests (not e2e) =="
uv run pytest -m "not e2e"
