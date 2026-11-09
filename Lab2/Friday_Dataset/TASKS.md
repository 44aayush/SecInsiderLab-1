# TASKS.md: Lab 2, Tasks 3 & 4 on the Friday DDoS file

Read `CLAUDE.md` first: it has the model-routing rules and the verified data facts.
Legend: **[O]** Opus (main session) · **[S]** Sonnet (dev/test/e2e/docs) · **[H]** Haiku (terminal/light).
Only Opus ticks boxes, and only after checking the acceptance criteria (AC).
Deadline **2026-11-11**.

Scope is exactly what `../Task3.png` / `../Task4.png` ask for, plus the tests needed to trust the results. Do not add tasks without the user's approval. All commands run from `Lab2/Friday_Dataset/` unless stated.

---

## P0: Setup

- [x] **F0.1 [H] Setup.** Commands run in `Lab2/`.
  1. `mkdir Friday_Dataset`
  2. `mv Friday-WorkingHours-Afternoon-DDos.csv Friday_Dataset/`
  3. In `Friday_Dataset/`, run `uv init --lib --name ddosids --no-workspace --vcs none --python 3.12`
  4. `uv add` the pinned dependencies (CLAUDE.md §3.1), then `uv add --dev pytest==9.2.0`
  5. Create `scripts/ tests/fixtures/ artifacts/ outputs/`
  6. Add `[tool.pytest.ini_options]` with `testpaths=["tests"]` and the `e2e` marker.

  *AC:* `uv run python -c "import sklearn, pandas, ddosids"` succeeds, and `sha256sum` of the CSV is the same before and after the move.

- [x] **F0.2 [S] Docs** (can run in parallel with F1).
  1. `Friday_Dataset/CLAUDE.md`: scope, verified facts, design decisions, layout, commands, gotchas. Routing points to `../CLAUDE.md` §1.
  2. `Friday_Dataset/TASKS.md`: the F-IDs below, with their ACs.
  3. `Lab2/CLAUDE.md`: add one line under the Dataset note, and add `Friday_Dataset/` to the §4 layout (the root file now has the Datasets section and the §4 layout; the Thursday project is now in `../Thursday_Dataset/`).
  4. `Lab2/.gitattributes`: add an LFS line for `Friday_Dataset/Friday-WorkingHours-Afternoon-DDos.csv`.

  *AC:* both new files exist; the two Lab2 edits are purely additive.

---

## P1: Task 3, Data Pre-processing

- [x] **F1 [S] Task 3: pre-processing.** Write `config.py`, `data.py`, `features.py`, `scripts/task3_preprocess.py`, `tests/fixtures/make_fixture.py` and the generated `sample_ddos.csv`, plus `tests/test_task3.py`.
  - The fixture has about 3k raw lines, keeps CRLF, and includes:
    - all 34 inf/NaN rows
    - about 1.5k DDoS and 1.3k BENIGN rows
    - every copy of about 120 BENIGN and 10 DDoS duplicate groups
  - Unit tests port the Thursday `test_task3.py` cases, including scaler-on-train-only and JSON == `SelectKBest` support.
  - The e2e test asserts:
    - raw counts 97,718 / 128,027
    - inf `{Flow Bytes/s: 30, Flow Packets/s: 34}` and NaN `{Flow Bytes/s: 4}`
    - NaN-row drop 34 `{BENIGN: 32, DDoS: 2}`
    - dedup 2,629 `{BENIGN: 2,618, DDoS: 11}`
    - the 10 constant columns and 8 identical columns (exact lists)
    - final shape `[223082, 61]`, `n_features == 59`
    - final counts 95,068 / 128,014
    - 20 distinct selected features

  *AC:* `pytest -m "not e2e"` runs in under 30 s and passes, and the e2e test passes.

- [x] **F1.R [H] Run.** Run the Task 3 script and both test sets, and paste the output verbatim.

  *AC:* the full output is reported, with nothing edited.

- [x] **F1.V [O] Review.** Check the output against CLAUDE.md §2.

  *AC:* every number matches §2 (223,082 × 59; 20 selected features).

---

## P2: Task 4, Logistic Regression + Decision Tree

- [x] **F2 [S] Task 4: LR + DT.** Write `models.py`, `evaluate.py`, `scripts/task4_train.py` and `tests/test_task4.py`.
  - For the 4 models, the outputs are: `metrics.json`, `comparison.csv`, `report_{key}.csv`, `cm_{key}.{png,pdf}`, the joblib files, `meta.json` (with `input_features` = 59 names), fit time, and inference ms per 1k flows.
  - Tests:
    - the files exist
    - the selected features match the Task 3 JSON
    - a joblib round trip reproduces the confusion matrix and macro-F1
  - e2e guards:
    - DT DDoS-F1 ≥ 0.99
    - LR-balanced DDoS recall ≥ 0.95
    - LR DDoS-F1 ≥ 0.90

  *AC:* all tests pass, and all 4 models and their outputs exist.

- [x] **F2.R [H] Run.** Run the Task 4 script and paste the comparison table and timings.

  *AC:* the full output is reported verbatim.

- [x] **F2.V [O] Review.**
  - Pick `REALTIME_MODEL`; `binary_dt_default` is expected.
  - Note the Destination-Port (port 80) shortcut risk.
  - Never judge on accuracy alone: use per-class P/R/F1, macro-F1 and the confusion matrix.

  *AC:* metrics are within the §2 baselines (DT F1 ≈ 0.9996, LR ≈ 0.974), and `REALTIME_MODEL` is chosen.

---

## P3: Real-time

- [x] **F3 [S] Real-time.**
  - Port `colmap.py`, `realtime/detector.py`, `scripts/realtime_detect.py` (`<flows.csv> [--rate N] [--model] [--models-dir] [--outputs-dir]`) and `tests/test_realtime.py`.
  - Set `config.REALTIME_MODEL` to the model chosen in F2.V.
  - Unit tests:
    - inf/NaN counting
    - Protocol-0 drop
    - a missing feature raises
    - Timestamp ordering
    - the CLI writes `predictions.csv` and `run_log.txt`
    - the V4 header from `../task2_lab2.pcap_Flow.csv` maps every feature (skip the test if the file is absent)
  - e2e parity test: the held-out test split, renamed with `ISCX_TO_V4` and streamed, gives predictions identical to `pipeline.predict`.

  *AC:* unit and e2e tests pass.

- [x] **F3.R [H] Run.** Run `uv run python scripts/realtime_detect.py ../task2_lab2.pcap_Flow.csv`. Paste the summary and every alert line.

  *AC:* 569 read, 22 Protocol-0 dropped, 547 classified.

- [x] **F3.V [O] Review.** Explain any alerts. Note the domain shift: CICFlowMeter V3 on the 2017 testbed vs V4 on the user's network.

  *AC:* every alert is explained, and the domain-shift caveat is stated honestly.

---

## P4: Report G8.Report2.pdf (LaTeX)

Decisions are in `CLAUDE.md` §9 (user, 2026-11-09). Friday results only, no comparison with Thursday. Build always with `latexmkrc_2` from inside `report/`.

- [x] **F4.0 [user] Screenshots.** Save SS27–SS38 into `SS/` (list in `CLAUDE.md` §9; SS26 is skipped by user decision). The common SS15/17/18/24/25 are already copied.

  *AC:* the files exist in `Friday_Dataset/SS/`.

- [x] **F4.1 [H] Template.** Copy the LaTeX template from `../Thursday_Dataset/reports/`: `thesis.tex`, `latexmkrc`, `latexmkrc_2`, `appendix.tex`, `bibliography.bib`, `includes/`, `chapters/`, `images/uni-logo.png`. No PDFs, `tables/`, `REVIEW.md` or `presentation/`.

  *AC:* the listed files exist in `report/` and nothing else was copied.

- [x] **F4.2 [S] Tables.** Write `scripts/make_report_tables.py` plus `tests/test_report_tables.py`. It writes `report/tables/*.tex`: t1_flows, t2_labels, t3_cleaning, t3_removed, t3_split, t3_scaling, t3_top20, t4_binary, t5_realtime (no multiclass).

  *AC:* output is deterministic, and key cells equal the outputs.

- [x] **F4.3 [S] Report text.** Preamble (title, paths), chapters, abstract and bibliography. Paths: `\graphicspath{{images/}{../SS/}{../outputs/task3/figures/}{../outputs/task4/figures/}}`, listings `../src/ddosids/...`.

  *AC:* 10–15 pages of main matter, and every number traces to the tables or outputs.

- [x] **F4.4 [H→O] Build and review.** Build with latexmkrc_2. Check the page count, undefined refs, missing glyphs, overfull boxes and pending screenshots. Opus reviews the numbers.

  *AC:* clean build, and Opus has checked the numbers against the tables.

- [x] **F4.5 [H] Deliverable.** `cp thesis.pdf G8.Report2.pdf` inside `report/`.

  *AC:* `report/G8.Report2.pdf` exists.

## P5: Presentation

- [x] **F5.1 [S] Deck.** `report/presentation/build_deck.js` builds `report/presentation/G8.Lab2.Presentation.pptx` from the Friday report (same theme as the Thursday deck).

  *AC:* `validate.py` passes, visual QA is clean (no overflow or overlap), and all numbers are Friday-only and traceable to the report tables or outputs.
