# Lab 2 — Machine Learning for Network Attack Detection

Security Insider Lab I, Uni Passau, group G8. Tasks 3 and 4 on the CIC-IDS2017 Friday DDoS file (`Friday-WorkingHours-Afternoon-DDos.csv`, 225,745 flows).

Specs: [lab-2.pptx](lab-2.pptx), [Task3.png](Task3.png), [Task4.png](Task4.png).
Deliverables: [report/G8.Report2.pdf](report/G8.Report2.pdf), [report/presentation/G8.Lab2.Presentation.pptx](report/presentation/G8.Lab2.Presentation.pptx).

## Tasks

**Task 3, pre-processing.** Strip column names, drop the duplicate `Fwd Header Length.1` column, replace inf with NaN and drop those rows, drop duplicate rows, drop constant and identical columns. Result: 223,082 rows x 59 features (DDoS 128,014, BENIGN 95,068). Stratified 70/30 split (random_state=42), then `MinMaxScaler` and `SelectKBest(chi2, k=20)` fitted on the training part only.

**Task 4, classification.** Binary BENIGN vs DDoS with Logistic Regression and Decision Tree, each with default and `class_weight="balanced"` (4 models, one sklearn pipeline each: scale, select, classify). Evaluated with per-class precision/recall/F1, macro-F1 and the confusion matrix.

**Real-time use.** `scripts/realtime_detect.py` streams the flows of `task2_lab2.pcap_Flow.csv` (CICFlowMeter V4, made from `task1_lab2.pcapng`) through the trained pipeline and prints one verdict per flow. The model is `config.REALTIME_MODEL` (`binary_dt_default`); the rationale is in the comment in `src/ddosids/config.py`.

## Layout

| Path | Content |
|---|---|
| `src/ddosids/` | package: config, data, features, models, evaluate, colmap, realtime/detector |
| `scripts/` | CLIs: `task3_preprocess.py`, `task4_train.py`, `realtime_detect.py`, `make_report_tables.py` |
| `tests/` | pytest suite and the small fixture `tests/fixtures/sample_ddos.csv` |
| `artifacts/` | generated: `clean.parquet`, split indices, selected features, `models/*.joblib` |
| `outputs/` | generated: `task3/`, `task4/`, `realtime/` (logs, CSVs, figures) |
| `report/` | LaTeX report, generated `tables/`, presentation |
| `SS/` | screenshots used in the report |

## Prerequisites

- [uv](https://docs.astral.sh/uv/) and Python 3.12
- git lfs: run `git lfs pull` so the CSVs are real files, not pointers

## Run everything

```bash
bash run.sh
```

A run regenerates the tracked `artifacts/` and `outputs/` (and `report/tables/`), so they show up in `git status`.

## Step by step

Run from `Lab2/`.

| Command | Writes |
|---|---|
| `uv sync` | `.venv` |
| `uv run python scripts/task3_preprocess.py` | `artifacts/clean.parquet`, `split_indices.json`, `selected_features_binary.json`; `outputs/task3/` |
| `uv run python scripts/task4_train.py` | `artifacts/models/`; `outputs/task4/` (metrics, comparison, figures) |
| `uv run python scripts/realtime_detect.py task2_lab2.pcap_Flow.csv` | `outputs/realtime/predictions.csv`, `run_log.txt` |
| `uv run python scripts/make_report_tables.py` | `report/tables/*.tex` (override with `--out`) |
| `uv run pytest -m "not e2e"` | nothing (`-m e2e` runs the full CSV, slow) |
