# CLAUDE.md: Security Insider Lab, Lab 2 (Tasks 3 & 4), Thursday Web Attacks

This sub-project does ML-based intrusion detection on CIC-IDS2017 flow features from the **Thursday** file `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`. It covers **Task 3 (Data Pre-processing)** and **Task 4 (Logistic Regression + Decision Tree, plus real-time use)**. Tasks 1 and 2 are already done; their outputs are listed in `../CLAUDE.md` §4.

- Course: Security Insider Lab, Uni Passau, group **G8**. Deadline: **2026-11-11**.
- Specs: `../Task3.png`, `../Task4.png`, and slides 9–10 of `lab-2.pptx` (in this folder). Progress is tracked in `TASKS.md`.
- **Scope rule:** implement only what the specs ask for, plus the tests needed to trust the results. Do not add tasks, features, or demos without the user's approval.
- Lab-wide rules (routing, real-time input, common gotchas, conventions, report) live in `../CLAUDE.md`. Model routing is `../CLAUDE.md` §1 and applies here unchanged. Where that section says "§2", read **§2 of this file**.
- The Friday DDoS implementation is the sibling `../Friday_Dataset/` (own uv project, own CLAUDE.md and TASKS.md). It does not replace this pipeline.

> **Dataset:** `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`, in this folder (`Thursday_Dataset/`). The user chose this file. Slide 8 names the Friday DDoS file, so this is a deliberate deviation. Do not switch datasets.

---

## 1. Model routing (MANDATORY)

See `../CLAUDE.md` §1 (same table and rules). Subagent prompts name the **`TASKS.md` ID of this folder** and tell the agent to read this file and that task's spec and AC first.

---

## 2. Verified data facts (Opus analysis, 2026-11-04)

- **170,366 rows × 79 columns** (78 features + `Label`). There are no Flow ID, IP, or Timestamp columns. `Destination Port` is present.
- **65 column names have stray spaces.** Run `df.columns.str.strip()` immediately after loading.
- **`Fwd Header Length` appears twice.** pandas names the second copy `Fwd Header Length.1`. Drop it.
- **Labels contain U+FFFD (`�`) instead of an en dash.** Read with `encoding="utf-8", encoding_errors="replace"`, then replace `�` with `-` and collapse whitespace.

  | Label | Raw count | After cleaning |
  |---|---:|---:|
  | `BENIGN` | 168,186 (98.72%) | 162,036 |
  | `Web Attack - Brute Force` | 1,507 (0.88%) | 1,470 |
  | `Web Attack - XSS` | 652 (0.38%) | 652 |
  | `Web Attack - Sql Injection` | 21 (0.012%) | 21 |

- **Infinity/NaN:**
  - `Flow Bytes/s` has 115 ±inf values and 20 NaN.
  - `Flow Packets/s` has 135 ±inf values.
  - 135 rows are affected in total, and **all of them are BENIGN**.
- **10 constant columns:** `Bwd PSH Flags`, `Fwd URG Flags`, `Bwd URG Flags`, `CWE Flag Count`, and the 6 `* Avg Bytes/Bulk | Packets/Bulk | Bulk Rate` columns.
- **Identical column pairs:**
  - `Fwd PSH Flags`≡`SYN Flag Count`
  - `RST Flag Count`≡`ECE Flag Count`
  - `Fwd Packet Length Mean`≡`Avg Fwd Segment Size`
  - `Total Fwd Packets`≡`Subflow Fwd Packets`
  - `Total Length of Fwd Packets`≡`Subflow Fwd Bytes`
  - `Total Backward Packets`≡`Subflow Bwd Packets`
  - `Bwd Packet Length Mean`≈`Avg Bwd Segment Size` (same quantity; differs in 2 rows by 1e-6 from CSV rounding, so it is treated as identical with `atol=1e-6`)
- **Duplicate rows:** 6,066 in the raw file, 14 of which are inf/NaN rows. In the cleaning order of §3.2, the dedup step drops **6,052** (6,015 BENIGN, 37 Brute Force).
- **Clean set (verified):** **164,179 rows × 60 features** (78 − 1 duplicate header − 10 constant − 7 identical). The 7 identical columns dropped are the second of each pair: `SYN Flag Count`, `ECE Flag Count`, `Avg Fwd Segment Size`, `Avg Bwd Segment Size`, `Subflow Fwd Packets`, `Subflow Fwd Bytes`, `Subflow Bwd Packets`.
- **Negative values exist.** `Init_Win_bytes_*` = −1 means "not observed", and a few `Flow Duration`/IAT values are negative. `chi2` rejects negative input, so it must run **after** MinMax scaling.
- **Every attack row has `Destination Port` = 80.**

### Preliminary baselines

These are sanity ranges only: 70/30 stratified split, rs=42, top-20 features.

| Setup | Result |
|---|---|
| Binary DT | attack F1 ≈ **0.98** |
| Binary LR, balanced | attack recall ≈ 0.99, precision ≈ 0.16 |
| Multiclass DT | macro-F1 ≈ **0.60**; Brute Force and XSS are heavily confused |
| Multiclass LR, default | predicts **everything as BENIGN** (accuracy 98.5% is meaningless) |

**Never report accuracy alone.** Always include per-class P/R/F1, macro-F1, and the confusion matrix.

---

## 3. Design decisions

1. **Targets:** binary (BENIGN vs ATTACK) is used for real time. Multiclass (4 labels) is also reported. Both targets use both algorithms.
2. **Cleaning order:**
   1. load and strip column names
   2. fix the labels
   3. drop `Fwd Header Length.1`
   4. replace ±inf with NaN
   5. **drop the NaN rows** (135 rows, all BENIGN)
   6. drop duplicate rows
   7. drop constant columns
   8. drop identical columns (`atol=1e-6`), so the 20 selected features are distinct
3. **Split before fitting anything.** Use a stratified 70/30 split with `random_state=42`. Fit the scaler and the selector on **train only**.
4. **Scaling:** `MinMaxScaler(clip=True)`, which keeps unseen real-time values inside [0,1].
5. **Feature selection:** `SelectKBest(chi2, k=20)`, run separately per target.
6. **One sklearn `Pipeline`:** `MinMaxScaler(clip=True) → SelectKBest(chi2, k=20) → classifier`. Persist it with joblib alongside `meta.json`. The real-time detector loads this same pipeline, which keeps training and serving consistent.
7. **Classifiers:** `LogisticRegression(max_iter=5000)` and `DecisionTreeClassifier(random_state=42)`, each trained in two variants: default and `class_weight="balanced"`.

---

## 4. Folder layout

```
Lab2/Thursday_Dataset/
├── CLAUDE.md  TASKS.md  README.md  pyproject.toml  uv.lock  .python-version   # uv; venv uses CPython 3.12
├── Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv   # DO NOT move/modify
├── lab-2.pptx                                   # course slides (moved here by the user, 2026-11-09)
├── SS/                                          # user's screenshots SS1-SS25 (no SS16)
├── reports/                                     # LaTeX report + presentation/; see §9
├── src/lab2ids/
│   ├── config.py  data.py  features.py  models.py  evaluate.py  colmap.py
│   └── realtime/  detector.py                    # streams a Task 2 flow CSV through the pipeline
├── scripts/   task3_preprocess.py  task4_train.py  realtime_detect.py  make_report_tables.py
├── tests/     unit + e2e (marker: e2e); fixtures/
├── artifacts/ GENERATED: models/*.joblib, meta.json, selected_features_*.json, split_indices.json, clean.parquet
└── outputs/   GENERATED: task3/, task4/, realtime/
```

The Task 1/2 files (`../task1_lab2.pcapng`, `../task2_lab2.pcap_Flow.csv`) are in the Lab2 root; see `../CLAUDE.md` §4. The report and screenshots are in this folder (`reports/`, `SS/`).

---

## 5. Commands

Run from `Lab2/Thursday_Dataset/`, which has its own `.venv`. **Always `cd` here before `uv run`.**

```bash
cd /home/aayush/Desktop/SecInsiderLab1/SecInsiderLab-1/Lab2/Thursday_Dataset
uv sync
uv run python scripts/task3_preprocess.py
uv run python scripts/task4_train.py --target both
uv run pytest -m "not e2e" -q                 # fast
uv run pytest -m e2e -q                         # full dataset

uv run python scripts/realtime_detect.py ../task2_lab2.pcap_Flow.csv [--rate 50]
uv run python scripts/make_report_tables.py     # writes reports/tables
```

---

## 6. Real-time (Thursday-specific)

The common input, architecture and domain-shift note are in `../CLAUDE.md` §6.

- **Real-time input:** `../task2_lab2.pcap_Flow.csv`. The flow CSV path is always a CLI argument; never hard-code it.
- **Model:** `REALTIME_MODEL` lives in `src/lab2ids/config.py` (currently `"binary_dt_default"`), not in `meta.json`, so re-running training cannot overwrite the choice. `--model` overrides it.
- **T5.4 expectations:** the run on `../task2_lab2.pcap_Flow.csv` completes with **22 dropped Protocol-0 rows** (15 ICMP, 4 IPv6, 3 ARP). All flows are BENIGN by construction, so every alert is a false positive to report honestly. If more than 10% of rows are dropped as unparsed, the flow file still has the old problem; report it to Opus.

---

## 7. Gotchas (Thursday-specific)

- **Multiclass LR needs `max_iter` ≥ 2000.** The balanced fit takes about 45 s.
- **Cache the cleaned data** to `artifacts/clean.parquet`. Unit tests use the fixture, never the 52 MB CSV.
- Common gotchas (V4 vs ISCX column names, the IPv6 / Protocol-0 cause, `task2_lab2.pcap_Flow.csv`, tshark, figures) are in `../CLAUDE.md` §7. The T5.1 column-name table is in `TASKS.md`.

---

## 8. Conventions

Same as `../CLAUDE.md` §8, with the code in `src/lab2ids`.

---

## 9. Report (`G8.Report2.pdf`, LaTeX): everything lives in `reports/`

The full plan is `/home/aayush/.claude/plans/cheeky-herding-goose.md`, and the steps are tracked in `TASKS.md` P4. The template comes from Lab 1 (`../../Lab1/G8_Report1_Version_2/G8_Report1_source/`). (Moved here from the root `../CLAUDE.md` on 2026-11-09.)

- **Location rule (user):** ALL LaTeX/report files and folders live under `Thursday_Dataset/reports/`, and the screenshots in `Thursday_Dataset/SS/` (both moved here by the user on 2026-11-09). Nothing report-related goes in the Lab2 root.
- **Build: ALWAYS with `latexmkrc_2`, from inside `reports/`** (user requirement):
  ```
  cd Thursday_Dataset/reports && latexmk -C -r latexmkrc_2 -jobname=thesis thesis.tex && latexmk -r latexmkrc_2 -jobname=thesis thesis.tex
  ```
  - The engine is LuaLaTeX + biber. `latexmkrc_2` deletes the temporary files, including `.lol`.
  - The final deliverable is `cp thesis.pdf G8.Report2.pdf`, run inside `reports/`.
- **Layout (`reports/`):**
  - `thesis.tex`, `latexmkrc`, `latexmkrc_2`, `bibliography.bib`, `appendix.tex`, `includes/`
  - `chapters/{introduction,task1_flows,task2_dataset,task3_preprocessing,task4_ml,task4_realtime,discussion}.tex`
  - `images/uni-logo.png`
  - `tables/*.tex`, generated by `cd Thursday_Dataset && uv run python scripts/make_report_tables.py`; the default `--out` is `reports/tables`
  - `REVIEW.md`, `G8.Report2.pdf`, and `presentation/` (`build_deck.js`, `G8.Lab2.Presentation.pptx`; `build_deck.js` resolves its paths relative to `Thursday_Dataset/`)
- **Paths are relative from `Thursday_Dataset/reports/`.** TeX's `openin_any=a` allows going up.
  - Figures are referenced in place: `\graphicspath{{images/}{../SS/}{../outputs/task3/figures/}{../outputs/task4/figures/}}`. Never copy them.
  - Listings use `\lstinputlisting{../src/lab2ids/...}`.
  - `\ssfig` checks `../SS/<name>.png`.
- **Numbers rule:** every metric or count in the report comes from `reports/tables/*.tex` (generated) or `HANDOVER_REPORT.md`. Never type numbers from memory or from agent transcripts.
- **Code listings** come from the real source files. Use DejaVu Sans Mono for code. `siunitx` is not installed.
- **Screenshots:** the user supplies SS15+ in `SS/` (list in the plan, R5). Until a file exists, `\ssfig` shows a "pending" box.
- **Content source:** `HANDOVER_REPORT.md` (deleted from the working tree on 2026-11-09; still in git history as `Lab2/HANDOVER_REPORT.md`). Style follows the Lab 1 report: concise "we" prose, `booktabs` tables, descriptive captions.
- **User decisions:** cover Tasks 1–4; the dataset choice was our own (web attacks are harder to detect than volumetric DDoS); short inline code excerpts; same authors as Lab 1. The main matter must be 10–15 pages.
