# TASKS.md: Lab 2, Tasks 3 & 4

Read this folder's `CLAUDE.md` first (verified data facts, design decisions) and `../CLAUDE.md` for the model-routing rules.
Moved from Lab2/ to Lab2/Thursday_Dataset/ on 2026-11-09 (user request). The report and screenshots now live in this folder's reports/ and SS/ (moved by the user the same day).
Legend: **[O]** Opus 5.5 (main session) · **[S]** Sonnet 5.5 (dev/test/e2e) · **[H]** Haiku 5.5 (browser/terminal/light).
Only Opus ticks boxes, and only after checking the acceptance criteria (AC).
Deadline **2026-11-11**.

Scope is exactly what `Task3.png` / `Task4.png` ask for, plus the tests needed to trust the results. Do not add tasks without the user's approval.

---

## P0: Setup

- [x] **T0.1 [H] Python project.**
  - In `Lab2/`, run `uv init --lib --name lab2ids --no-workspace --vcs none`.
  - Add dependencies: `uv add pandas numpy scikit-learn matplotlib joblib pyarrow` and `uv add --dev pytest`.
  - Create `scripts/ tests/fixtures/ artifacts/ outputs/`.
  - Add `[tool.pytest.ini_options]` to `pyproject.toml` with marker `e2e`.

  *AC:* `uv run python -c "import sklearn, pandas, lab2ids"` succeeds.

---

## P1: Task 3, Data Pre-processing

- [x] **T3.1 [S] Load & analyze labels** (`src/lab2ids/config.py`, `data.py`).
  - `load_raw()`: read with `encoding="utf-8", encoding_errors="replace"`, then strip column names.
  - `normalize_labels()`: replace `�` with `-` and collapse whitespace.
  - `label_summary()`: counts and percentages per label.

  *AC:* raw counts are exactly 168186 / 1507 / 652 / 21.

- [x] **T3.2 [S] Manage Infinity/NaN + cleaning** (`data.py`). Implement `clean(df) -> (df, report)`, following the step order in CLAUDE.md §3.2. Every step writes its counts to `outputs/task3/cleaning_report.json`. Add a `binary_label` column.

  *AC:* the report shows:
  - inf: 115 (`Flow Bytes/s`) and 135 (`Flow Packets/s`); NaN: 20
  - 135 rows dropped, all of them BENIGN
  - 6052 duplicate rows dropped (6015 BENIGN, 37 Brute Force)
  - 10 constant columns
  - 164,179 rows × 60 features left, with no inf or NaN remaining

- [x] **T3.3 [S] Min-max scaling.**
  - Make a stratified 70/30 split (rs=42) and save the test indices to `artifacts/split_indices.json`.
  - Fit `MinMaxScaler(clip=True)` on train only.
  - Save `describe()` before and after scaling to `outputs/task3/`.

  *AC:* train min/max are exactly 0/1 for every column, and every class is present in both splits.

- [x] **T3.4 [S] SelectKBest, 20 best features** (`features.py`). Run `SelectKBest(chi2, k=20)` on the scaled train set, once per target (`binary`, `multiclass`).
  - Save the scores table to `outputs/task3/`.
  - Save a top-20 bar chart as PNG and PDF.
  - Save the selected features to `artifacts/selected_features_{target}.json`.

  *AC:* 20 distinct features per target.

- [x] **T3.5 [S] CLI + tests.**
  - `scripts/task3_preprocess.py` runs T3.1–T3.4, prints a summary, and caches `artifacts/clean.parquet`.
  - Build `tests/fixtures/sample_iscx.csv` (about 3k stratified rows) with a generator script. It must include:
    - all 21 SQLi rows
    - some inf/NaN rows
    - some duplicate rows
    - the duplicate header
    - the original broken label bytes
  - Write unit tests for each step and a check that the scaler is fit on train only.
  - Write an `e2e` test that runs the CLI on the full CSV and asserts the T3.2 numbers.

  *AC:* `pytest -m "not e2e"` passes in under 30 s, and `pytest -m e2e` passes.

- [x] **T3.6 [H] Run & collect.** Run the T3.5 script and tests, and paste the output back verbatim.
- [x] **T3.7 [O] Review** against CLAUDE.md §2.

---

## P2: Task 4, Logistic Regression & Decision Tree

- [x] **T4.1 [S] Pipelines** (`models.py`).
  - Build `Pipeline([MinMaxScaler(clip=True), SelectKBest(chi2, k=20), clf])` for `LogisticRegression(max_iter=5000)` and `DecisionTreeClassifier(random_state=42)`.
  - Train each in two variants: default and `class_weight="balanced"`. The balanced variant is needed because default LR predicts all BENIGN.
  - Cover both targets, which makes 8 models in total. Train on the T3.3 train split.

  *AC:* each pipeline's selected features equal the T3.4 JSON for its target.

- [x] **T4.2 [S] Evaluation** (`evaluate.py`). For each model on the test split, produce:
  - a classification report (per-class P/R/F1, macro-F1, with accuracy shown alongside)
  - a confusion matrix figure
  - fit time and inference time per 1k flows

  Write everything to `outputs/task4/`: `metrics.json`, a single comparison table, and the figures.

- [x] **T4.3 [S] Persist + CLI + tests.**
  - Save each pipeline with `joblib` to `artifacts/models/{target}_{model}.joblib`.
  - Write `artifacts/meta.json` with the input feature order, selected features, classes, and library versions.
  - `scripts/task4_train.py` takes `--target binary|multiclass|both`.
  - Tests: a save/load round trip must reproduce the stored metrics.
  - `e2e` regression guards:
    - binary DT attack-F1 ≥ 0.95
    - binary LR-balanced attack recall ≥ 0.90
    - multiclass DT macro-F1 ≥ 0.50

- [x] **T4.4 [H] Run & collect.** Run `task4_train.py --target both` and the tests, then paste back the comparison table and timings.
- [x] **T4.5 [O] Review & pick the real-time model**, expected to be the binary DT. Record it as `REALTIME_MODEL` in `src/lab2ids/config.py`, not in `meta.json`, so re-running training cannot overwrite the choice.

---

## P3: Task 4, Real-time use on network traffic (LAST phase)

Do this phase only after P1 and P2 are done.

**Real-time input:** `task2_lab2.pcap_Flow.csv` (Task 2 flows), made from `task1_lab2.pcapng` (Task 1 capture).
- Reviewed by Opus on 2026-11-04: 99.9% IPv4, 547 of 569 flows valid.
- Never hard-code these files. The flow CSV path is a CLI argument.
- T5.4 is unblocked once P2 is done.

- [x] **T5.1 [S] Column mapping** (`colmap.py`).
  - `V4_TO_ISCX` maps CICFlowMeter V4 names to the training names. Use a normalized-name match plus the 20 overrides below.
  - `ISCX_TO_V4` is the inverse.
  - `META_COLS = [Flow ID, Src IP, Src Port, Dst IP, Protocol, Timestamp]`.

  | ISCX (training) | CICFlowMeter V4 |
  |---|---|
  | Destination Port | Dst Port |
  | Total Fwd Packets | Total Fwd Packet |
  | Total Backward Packets | Total Bwd packets |
  | Total Length of Fwd Packets | Total Length of Fwd Packet |
  | Total Length of Bwd Packets | Total Length of Bwd Packet |
  | Min Packet Length | Packet Length Min |
  | Max Packet Length | Packet Length Max |
  | CWE Flag Count | CWR Flag Count |
  | Avg Fwd Segment Size | Fwd Segment Size Avg |
  | Avg Bwd Segment Size | Bwd Segment Size Avg |
  | Fwd Avg Bytes/Bulk | Fwd Bytes/Bulk Avg |
  | Fwd Avg Packets/Bulk | Fwd Packet/Bulk Avg |
  | Fwd Avg Bulk Rate | Fwd Bulk Rate Avg |
  | Bwd Avg Bytes/Bulk | Bwd Bytes/Bulk Avg |
  | Bwd Avg Packets/Bulk | Bwd Packet/Bulk Avg |
  | Bwd Avg Bulk Rate | Bwd Bulk Rate Avg |
  | Init_Win_bytes_forward | FWD Init Win Bytes |
  | Init_Win_bytes_backward | Bwd Init Win Bytes |
  | act_data_pkt_fwd | Fwd Act Data Pkts |
  | min_seg_size_forward | Fwd Seg Size Min |

  *AC:* a test maps the CICFlowMeter V4 header (take it from `task2_lab2.pcap_Flow.csv`) with no unmapped features.

- [x] **T5.2 [S] Real-time detector + CLI** (`realtime/detector.py`, `scripts/realtime_detect.py <flows.csv> [--rate N]`).
  - **Input:** stream the Task 2 flow CSV row by row in `Timestamp` order. `--rate` sets flows per second (default: as fast as possible).
  - **Processing steps:**
    1. Map the columns with `V4_TO_ISCX`.
    2. Reindex to the input feature order.
    3. Set inf/NaN to 0.
    4. Drop `Protocol==0` / unparsed rows and count them.
    5. Predict with the `config.REALTIME_MODEL` pipeline (overridable with `--model`).
  - **Output:**
    - one console line per flow: `ts src:sport → dst:dport/proto BENIGN|ATTACK p=…`
    - `outputs/realtime/predictions.csv`
    - a summary at the end: flows, alerts, dropped rows
  - **Unit tests** on a few synthetic rows (inf/NaN, Protocol 0).

- [x] **T5.3 [S] Parity e2e test.** Rename the held-out ISCX test split to V4 column names with `ISCX_TO_V4`, then stream it through the detector.
  *AC:* predictions are identical to offline `pipeline.predict`.

- [x] **T5.4 [H] Run on the Task 1/2 traffic** (`task2_lab2.pcap_Flow.csv`, from `task1_lab2.pcapng`; all flows are BENIGN by construction).
  - Run `realtime_detect.py task2_lab2.pcap_Flow.csv`. Expect 22 dropped Protocol-0 rows: 15 ICMP, 4 IPv6, 3 ARP.
  - Paste back the summary and every alert line.
  - *AC:* the run completes. If more than 10% of rows are dropped as unparsed, report it to Opus, because it means the flow file still has the old problem.

- [x] **T5.5 [O] Review** the real-time results:
  - Is the traffic in the user's Task 1 capture benign, or does it contain attacks? Ask the user if it is unclear.
  - Explain any alerts.
  - Note how this traffic differs from the training data: CICFlowMeter V3 vs V4, a different network, and TCP-stack features such as `Init_Win_bytes_*`.

---

## P4: Report `G8.Report2.pdf` (LaTeX)

Plan: `/home/aayush/.claude/plans/cheeky-herding-goose.md`. **All report files live in `reports/`** (user rule), and the PDF is always built inside `reports/` with `latexmkrc_2` (CLAUDE.md §9).

- [x] **R0 [O] Housekeeping.** Memory (latexmkrc_2), CLAUDE.md §9, this phase.
- [x] **R1 [H] Copy the template to the Lab2 root.** Copy `thesis.tex`, `latexmkrc`, `latexmkrc_2`, `appendix.tex`, `bibliography.bib`, `includes/`, `chapters/` and `images/uni-logo.png` only. Do not copy the PDFs, the `fig_*.png` images or build artifacts.
- [x] **R2 [S] Preamble + skeleton.** Moved to `reports/` afterwards (user rule); the build was re-verified from `reports/`.
  - Title, graphics path, `listings` with DejaVu Sans Mono, `subcaption`, and the `\ssfig` placeholder macro.
  - The new chapter `\input`s; delete the Lab 1 chapters.
  - *AC:* the skeleton compiles with the latexmkrc_2 command.
- [x] **R3 [S] Table generator.** `scripts/make_report_tables.py` writes `tables/*.tex` from the output CSV/JSON; `tests/test_report_tables.py` tests it.
  - *AC:* deterministic, and key cells equal the CSV values.
- [x] **R4 [S] Chapters + abstract + bibliography** from `HANDOVER_REPORT.md`, with Listings 1–3, figures and generated tables.
  - *AC:* the main matter is about 13 pages and every number traces to `tables/` or HANDOVER.
- [x] **R5 [user] Screenshots.** SS15 and SS17–SS23 were received 2026-11-04 (SS19–SS23 are the Task 3 console output). SS24 (`sysctl` disabling IPv6) and SS25 (CICFlowMeter GUI conversion) were received 2026-11-06. SS25 replaces the SS16 placeholder, and SS16 is not used.
- [x] **R6 [H→O] Build + review.**
  - Haiku: page count, undefined refs/citations, missing glyphs, overfull boxes.
  - Opus: page-by-page check of the numbers against the tables and HANDOVER.
- [x] **R7 [H] Final.** Verify the BibTeX entries (web search), rebuild after the screenshots, then `cp reports/thesis.pdf reports/G8.Report2.pdf`.
  - Done 2026-11-04: BibTeX verified via Crossref/JMLR, with DOIs and pages added. `G8.Report2.pdf` was built (20 pages, 14 main matter, 0 warnings).
  - 2026-11-06: SS24 and SS25 added, figures moved next to their text (no float-only pages), rebuilt with latexmkrc_2. Result: 21 pages, 15 main matter, 0 warnings, 0 placeholders. `G8.Report2.pdf` updated.
