# CLAUDE.md: Security Insider Lab, Lab 2 (Tasks 3 & 4), Friday DDoS

This sub-project does ML-based intrusion detection on CIC-IDS2017 flow features from the **Friday** file `Friday-WorkingHours-Afternoon-DDos.csv`. It covers **Task 3 (Data Pre-processing)** and **Task 4 (Logistic Regression + Decision Tree, plus real-time use)**.

- Course: Security Insider Lab, Uni Passau, group **G8**. Deadline: **2026-11-11**.
- Specs: `../Task3.png`, `../Task4.png`, and slides 9–10 of `../Thursday_Dataset/lab-2.pptx`. Slide 8 names this Friday file. Progress is tracked in `TASKS.md`.
- This is a **parallel, self-contained implementation** (user request, 2026-11-09). It does not replace the Thursday pipeline in `../Thursday_Dataset/src/lab2ids/` (the Thursday project now lives in `../Thursday_Dataset/`), and it never imports `lab2ids`.
- **Scope rule:** same as `../CLAUDE.md`. Implement only what the specs ask for, plus the tests needed to trust the results. Do not add tasks, features, or demos without the user's approval.
- **Out of scope (plan decision 6):** the Destination-Port ablation. (The report and the presentation were requested by the user on 2026-11-09; see §9 and §10.)

---

## 1. Model routing (MANDATORY)

Same table and rules as `../CLAUDE.md` §1.

| Work type | Model | How to delegate |
|---|---|---|
| Analysis, planning, design decisions, interpreting metrics, reviewing subagent output | **Opus** (main session) | inline |
| Development: writing code, unit tests, e2e tests, debugging | **Sonnet** | `Agent(subagent_type="general-purpose", model="sonnet", ...)` |
| Presentations and documents, report text | **Sonnet** | `Agent(subagent_type="general-purpose", model="sonnet", ...)` |
| Browser use, running terminal commands, env setup, running scripts and collecting output, light tasks | **Haiku** | `Agent(subagent_type="general-purpose", model="haiku", ...)` |

1. Subagents start cold. Each prompt names the **`Friday_Dataset/TASKS.md` F-ID** and tells the agent to read this file, `TASKS.md` and the Thursday source it ports first.
2. One task per subagent, one result back. Independent tasks may run in parallel.
3. Haiku runs commands and reports output verbatim. It does **not** edit `src/`. Opus routes code fixes to Sonnet.
4. Opus checks every result against its AC and against §2, then ticks the box in `TASKS.md`. **Only Opus ticks boxes.**
5. `sudo` is not available non-interactively. Hand any root step to the user as a `! sudo ...` command.

---

## 2. Verified data facts (Haiku profile, 2026-11-09; pandas 3.1.0, sklearn 1.9.1)

- **225,745 rows × 79 columns**, CRLF line endings, pure ASCII, no blank lines. The header is **identical to Thursday's**: 65 names with stray spaces, and `Fwd Header Length.1` is an exact copy that gets dropped.
- **Labels are clean.** There is no U+FFFD. DDoS is the **majority class**.

  | Label | Raw count | After cleaning |
  |---|---:|---:|
  | `DDoS` | 128,027 (56.7%) | 128,014 |
  | `BENIGN` | 97,718 | 95,068 |

- **Infinity/NaN (all +inf):**
  - `Flow Bytes/s`: 30 inf and 4 NaN
  - `Flow Packets/s`: 34 inf
  - 34 rows are affected: **32 BENIGN, 2 DDoS**. Unlike Thursday, a few attack rows are dropped.
- **Duplicates:** 2,633 raw (4 of them are inf/NaN rows). In the cleaning order of §3, the dedup step drops **2,629** (2,618 BENIGN, 11 DDoS).
- **Constant columns:** the same 10 as Thursday.
- **Identical pairs: 8.** These are Thursday's 7 plus `Total Length of Bwd Packets` ≡ `Subflow Bwd Bytes`. `Avg Bwd Segment Size` differs in 2 rows, within `atol=1e-6`.
- **Clean set: 223,082 rows × 59 features** (78 − 1 − 10 − 8). DDoS 128,014, BENIGN 95,068. Including `Label` and `binary_label`, the final shape is `[223082, 61]`.
- **Negative values exist** (`Init_Win_bytes_*` = −1, a few IAT/duration values), so `chi2` must run after MinMax scaling.
- **DDoS is effectively all port 80** (128,011 / 128,014). BENIGN is mostly 53 / 443 / 80.
- **Split 70/30 (rs=42):** train 156,157 / test 66,925, with 38,404 DDoS in test.
- **chi2 top-20 (preview):** URG Flag Count, Destination Port, Bwd Packet Length Max/Std/Mean, Bwd IAT Total, Max Packet Length, Packet Length Mean, …

### Preliminary baselines

Sanity ranges for the e2e guards.

| Model | DDoS F1 | Confusion `[[TN, FP], [FN, TP]]` |
|---|---:|---|
| DT default / balanced | 0.9996 | `[[28514, 7], [25, 38379]]` |
| LR default | 0.9739 | 2,008 FP, 45 FN |
| LR balanced | 0.9744 | 1,974 FP, 45 FN |

- LR converges in 48 iterations.
- DT importance: Fwd Packet Length Max 0.58, **Destination Port 0.35**.

### Real-time preview

On `../task2_lab2.pcap_Flow.csv`: 547 flows after the Protocol-0 drop, no missing features.

| Model | Alerts |
|---|---:|
| DT default / balanced | 0 |
| LR default | 69 |
| LR balanced | 64 |

The LR alerts are mostly on port 443, which is a domain-shift effect.

**Never report accuracy alone.** Always include per-class P/R/F1, macro-F1, and the confusion matrix.

---

## 3. Design decisions

1. **Self-contained uv project.** `Friday_Dataset/` has its own `pyproject.toml`, `.python-version` (3.12), `.venv` and package **`ddosids`**. Dependencies are pinned to `../Thursday_Dataset/uv.lock`: pandas==3.1.0, numpy==2.5.4, scikit-learn==1.9.1, matplotlib==3.11.2, joblib==1.6.0, pyarrow==26.0.1, and pytest==9.2.0 (dev).
2. **Cleaning order:**
   1. load and strip column names
   2. normalise labels (U+FFFD fix kept; it is a no-op here)
   3. drop `Fwd Header Length.1`
   4. replace ±inf with NaN
   5. **drop the NaN rows** (34 rows: 32 BENIGN, 2 DDoS)
   6. drop duplicate rows
   7. drop constant columns
   8. drop identical columns (`atol=1e-6`)
3. **Split before fitting anything.** Stratified 70/30 split, `random_state=42`. Fit the scaler and the selector on **train only**.
4. **Scaling:** `MinMaxScaler(clip=True)`. **Selection:** `SelectKBest(chi2, k=20)`.
5. **One sklearn `Pipeline`:** `MinMaxScaler(clip=True) → SelectKBest(chi2, k=20) → classifier`. Persist it with joblib alongside `meta.json`. The real-time detector loads this same pipeline.
6. **4 models, binary target only.** With two labels, multiclass would duplicate binary. The models are `binary_{lr,dt}_{default,balanced}`: `LogisticRegression(max_iter=5000)` and `DecisionTreeClassifier(random_state=42)`, each default and `class_weight="balanced"`.
7. **Class names** are `BENIGN` and `DDoS` everywhere, including the real-time verdict.
8. **Data-driven drops.** Constant and identical columns are detected from the data. Only the e2e test pins the Friday numbers of §2.
9. **Real-time:** port the Thursday detector (V4→ISCX column map, Protocol-0 drop, inf/NaN→0, persisted pipeline, one line per flow). The expected model is `binary_dt_default`, confirmed at the F2 review.
10. Every row and column drop is logged with its count.

---

## 4. Layout

```
Lab2/Friday_Dataset/
├── CLAUDE.md  TASKS.md  pyproject.toml  uv.lock  .python-version
├── Friday-WorkingHours-Afternoon-DDos.csv          # moved here (mv)
├── src/ddosids/  config.py data.py features.py models.py evaluate.py colmap.py realtime/detector.py
├── scripts/      task3_preprocess.py  task4_train.py  realtime_detect.py
├── tests/        test_task3.py test_task4.py test_realtime.py  fixtures/{make_fixture.py, sample_ddos.csv}
├── artifacts/    GENERATED: clean.parquet, split_indices.json, selected_features_binary.json, models/*.joblib, models/meta.json
├── outputs/      GENERATED: task3/ task4/ realtime/  (same file names as Thursday, binary only)
├── SS/           screenshots: the 5 common ones (SS15/17/18/24/25, copied from ../Thursday_Dataset/SS/, sha256-verified) plus SS26+ to come
└── report/       LaTeX report (written, in review; see §9)
```

---

## 5. Commands

Run from `Lab2/Friday_Dataset/`, which has its own `.venv`. **Always `cd` here before `uv run`.**

```bash
cd /home/aayush/Desktop/SecInsiderLab1/SecInsiderLab-1/Lab2/Friday_Dataset
uv sync
uv run python scripts/task3_preprocess.py      # 223,082 rows × 59 features, 20 features selected
uv run python scripts/task4_train.py           # 4 models; DT DDoS-F1 ≈ 0.9996, LR ≈ 0.974
uv run python scripts/realtime_detect.py ../task2_lab2.pcap_Flow.csv   # 547 classified, 22 dropped
uv run pytest -m "not e2e" -q                  # < 30 s
uv run pytest -m e2e -q                        # full Friday CSV + parity
git -C .. status --short                       # changes only under Friday_Dataset/, plus CLAUDE.md and .gitattributes
```

---

## 6. Real-time

- **Input:** `../task2_lab2.pcap_Flow.csv`, made from `../task1_lab2.pcapng`. The flow CSV path is always a CLI argument; it is never copied or hard-coded.
- **Pipeline:** colmap (V4 → ISCX names) → drop `Protocol==0` rows (expect **22**: 15 ICMP, 4 IPv6, 3 ARP) → inf/NaN→0 → joblib pipeline → per-flow verdict (`BENIGN` / `DDoS`).
- **Expect domain shift.** The training data was produced by CICFlowMeter V3 on the 2017 testbed; the Task 2 flows come from V4 on the user's network. Report any alerts honestly.

---

## 7. Gotchas

- **CRLF line endings** in the raw CSV (and in the fixture).
- **2 DDoS rows are lost in the inf/NaN drop** (unlike Thursday, where all dropped rows were BENIGN).
- **Destination Port shortcut risk.** DDoS is effectively all dst port 80, and Destination Port has DT importance **0.35**. Report this honestly; no ablation is done.
- **LR gives many false positives on port-443 Task 2 flows** (preview: 64–69 of 547).
- **DDoS is the majority class,** so `class_weight="balanced"` changes little.
- **LR converges in about 48 iterations.**
- **`chi2` needs MinMax first** (negative values exist).
- **The detector must always drop `Protocol==0` rows and log the count.** See `../CLAUDE.md` §7 (Gotchas, common) for the CICFlowMeter IPv6 cause.
- **Cache the cleaned data** to `artifacts/clean.parquet`. Unit tests use the fixture `tests/fixtures/sample_ddos.csv`, never the 77 MB CSV.
- **Save figures as PNG (200 dpi) and PDF.**

---

## 8. Conventions

- Use type hints and small functions in `src/ddosids`. Scripts are thin argparse CLIs.
- Use `random_state=42` everywhere. Log every row and column drop with its count.
- Do not create a git repo or commit unless the user asks.

---

## 9. Report (written, in review): `G8.Report2.pdf`

User decisions, 2026-11-09. Steps are tracked in `TASKS.md` P4. Status: text written and builds cleanly (19 pages in total, 13 of main matter); in review.

- **Location and deliverable:** `Friday_Dataset/report/` (singular); the deliverable is `G8.Report2.pdf` (made by the review step with `cp report/thesis.pdf report/G8.Report2.pdf`).
- **Scope:** full Tasks 1–4, same chapter structure as the Thursday report. The Task 1/2 chapters reuse the Thursday text and the common screenshots. Task 3/4 cover the **Friday results only, with NO comparison with Thursday**. Target 10–15 pages of main matter.
- **Build:** same rule as Thursday. ALWAYS with `latexmkrc_2`, from inside `Friday_Dataset/report/`:
  ```
  cd Friday_Dataset/report && latexmk -C -r latexmkrc_2 -jobname=thesis thesis.tex && latexmk -r latexmkrc_2 -jobname=thesis thesis.tex
  ```
- **Screenshots** are taken by the user and saved in `Friday_Dataset/SS/`, all run from `Friday_Dataset/`. The report uses:
  - common, copied from Thursday: SS15 Wireshark protocol hierarchy, SS17 Task 2 flow CSV in LibreOffice, SS24 `sysctl` disabling IPv6, SS25 CICFlowMeter GUI conversion (SS18, the Steam requests, is not used)
  - SS27: Task 3 raw label summary (`uv run python scripts/task3_preprocess.py`)
  - SS28: Task 3 cleaning steps ("Final: 223082 rows x 59 features")
  - SS29: final label summary + 70/30 split counts
  - SS30: top-20 chi2 features (binary)
  - SS31 / SS32 / SS33 / SS34: Task 4 blocks `binary_lr_default` / `binary_lr_balanced` / `binary_dt_default` / `binary_dt_balanced` (`uv run python scripts/task4_train.py`); the report shows SS33
  - SS35: the 4-model comparison table
  - SS36: `uv run pytest -m "not e2e" -q` (24 passed, 3 deselected)
  - SS37: `uv run pytest -m e2e -q` (3 passed, 24 deselected)
  - SS38: real-time detector summary (569 read, 22 dropped, 547 classified, 0 alerts), from `uv run python scripts/realtime_detect.py ../task2_lab2.pcap_Flow.csv`
  - **SS26 is skipped (user decision) and is not used.**
- **Order:** take the screenshots BEFORE generating the report tables, because re-running Task 4 changes only the timings.
- **Numbers rule:** every number comes from the generated `report/tables/*.tex` (default `--out` of `scripts/make_report_tables.py` is `report/tables`) or the Friday `outputs/`. The Task 1/2 numbers come from the reused Thursday chapters.
- **Paths, relative from `Friday_Dataset/report/`:** `\graphicspath{{images/}{../SS/}{../outputs/task3/figures/}{../outputs/task4/figures/}}`; listings `\lstinputlisting{../src/ddosids/...}`.

## 10. Presentation

User request, 2026-11-09. The deck is `report/presentation/G8.Lab2.Presentation.pptx` (15 slides, speaker notes on every slide), generated by `report/presentation/build_deck.js`.

- **Build:** `cd report/presentation && node build_deck.js` (needs `pptxgenjs`; if `require` fails, run `npm install pptxgenjs` somewhere and set `NODE_PATH`).
- **Theme:** same as the Thursday deck (Cambria/Calibri, `LAYOUT_WIDE`, same layouts), theme name "G8 Lab2 Passau Friday".
- **Numbers rule:** every number comes from the Friday report tables, `outputs/`, or the Task 1 chapter. Friday only: no comparison with Thursday.
