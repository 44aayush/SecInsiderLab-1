# CLAUDE.md: Security Insider Lab, Lab 2 (Tasks 3 & 4)

This lab does ML-based intrusion detection on CIC-IDS2017 flow features. The workspace covers **Task 3 (Data Pre-processing)** and **Task 4 (Logistic Regression + Decision Tree, plus real-time use)**. Tasks 1 and 2 are already done; their outputs are listed in §4.

- Course: Security Insider Lab, Uni Passau, group **G8**. Deadline: **2026-11-11**.
- Specs: `Task3.png`, `Task4.png`, and slides 9–10 of `lab-2.pptx`. Progress is tracked in `TASKS.md`.
- **Scope rule:** implement only what the specs ask for, plus the tests needed to trust the results. Do not add tasks, features, or demos without the user's approval.

> **Dataset:** `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`. The user chose this file. Slide 8 names the Friday DDoS file, so this is a deliberate deviation. Do not switch datasets.

---

## 1. Model routing (MANDATORY)

The main session runs on **Opus 5.5**. It orchestrates, analyzes, and reviews. It does not write bulk code or run long command sequences itself, and delegates with the `Agent` tool:

| Work type | Model | How to delegate |
|---|---|---|
| Analysis, planning, design decisions, interpreting metrics, reviewing subagent output | **Opus 5.5** (main session) | inline |
| Development: writing code, unit tests, e2e tests, debugging | **Sonnet 5.5** | `Agent(subagent_type="general-purpose", model="sonnet", ...)` |
| Browser use, running terminal commands, env setup, running scripts and collecting output, light tasks | **Haiku 5.5** | `Agent(subagent_type="general-purpose", model="haiku", ...)` |

Delegation rules:

1. Subagents start cold. Each prompt names the **TASKS.md ID** and tells the agent to read `CLAUDE.md` plus that task's spec and AC first.
2. Give each subagent one task and expect one result back. Independent tasks may run in parallel.
3. Haiku runs commands and reports output verbatim. It does **not** edit `src/`. Opus routes code fixes to Sonnet.
4. Opus checks every result against its AC and against §2, then ticks the box in `TASKS.md`. Subagents never tick boxes.
5. `sudo` is not available non-interactively. Hand any root step to the user as a `! sudo ...` command.

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

## 4. Repository layout

```
Lab2/
├── CLAUDE.md  TASKS.md  pyproject.toml          # uv; venv uses CPython 3.12 (.python-version)
├── Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv   # DO NOT move/modify
├── task1_lab2.pcapng              # Task 1 capture: 81,110 frames, 347 s, 99.9% IPv4 (IPv6 off), benign
├── task2_lab2.pcap_Flow.csv       # CICFlowMeter V4 flows of task1_lab2.pcapng (569 flows); REAL-TIME INPUT
├── CICFlowMeter/                  # Java tool used by the user in Task 1/2 to make flows
├── src/lab2ids/
│   ├── config.py  data.py  features.py  models.py  evaluate.py  colmap.py
│   └── realtime/  detector.py                    # streams a Task 2 flow CSV through the pipeline
├── scripts/   task3_preprocess.py  task4_train.py  realtime_detect.py
├── tests/     unit + e2e (marker: e2e); fixtures/
├── artifacts/ GENERATED: models/*.joblib, meta.json, selected_features_*.json, split_indices.json
└── outputs/   GENERATED: task3/, task4/, realtime/
```

---

## 5. Commands

```bash
uv sync
uv run python scripts/task3_preprocess.py
uv run python scripts/task4_train.py --target both
uv run pytest -m "not e2e" -q                 # fast
uv run pytest -m e2e -q                         # full dataset

uv run python scripts/realtime_detect.py <task2_flows.csv> [--rate 50]
```

---

## 6. Real-time architecture (implemented last, in P3)

```
 Task 1 pcap ──(user runs CICFlowMeter, Task 1/2)──► Task 2 flow CSV (V4 columns)
                                                          │ streamed row by row, Timestamp order
                                                          ▼
   colmap (V4 → ISCX names) → inf/NaN→0, drop Protocol-0 rows → joblib Pipeline → per-flow verdict
```

- **Real-time input:** `task2_lab2.pcap_Flow.csv`, made from `task1_lab2.pcapng` (benign browsing, 2026-11-04, 16:05–16:10). The flow CSV path is always a CLI argument; never hard-code it.
- **Expect domain shift.** The training data was produced by CICFlowMeter V3 on the 2017 testbed; the Task 2 flows come from V4 on a different network. Report any false positives honestly.

---

## 7. Gotchas

- **Column names differ between CICFlowMeter V4 and ISCX.** 20 names differ; TASKS.md T5.1 has the table. The remaining 57 match after normalization. All 77 features map (verified). V4's metadata columns are for display only and must never be used as features.
- **Earlier captures (deleted; the files were 89–98% IPv6) produced bogus flows.** 85–95% of their flows had `Protocol=0` and `Dst Port=0`, implausible IPs (e.g. `136.225.0.0 → 160.0.176.82`) and 0 backward packets. If a future capture shows this, IPv6 was on.
  **Verified cause:** CICFlowMeter hard-codes `readIP6 = false` (`Cmd.java:126`, `ReadPcapFileWorker.java:152`). Every non-IPv4 frame (IPv6, ARP, HomePlug) falls into `getVPNInfo()`, which force-parses the frame as IPv4 from byte 0. The "src IP" is therefore EtherType + 2 bytes (`134.221.x` = `86 DD` IPv6, `136.225` = `88 E1` HomePlug, `8.6` = ARP). The "dst IP" is the IPv6 flow label + payload length. The IPv4 flows themselves are parsed correctly.
  The detector must always drop `Protocol==0` rows and log the count.
- **`task2_lab2.pcap_Flow.csv` (from `task1_lab2.pcapng`) is the good file.** IPv6 was off for the capture. The user renamed it from `benign_lab2_3.*`; the old `task1_lab2.pcap`/`task2_lab2.pcap_Flow.csv` are gone.
  - 569 flows: 162 TCP, 385 UDP, 22 with Protocol 0
  - the 22 Protocol-0 rows are 15 real ICMP flows (CICFlowMeter gives every non-TCP/UDP flow protocol 0) plus 4 IPv6 and 3 ARP leftovers
  - CICFlowMeter only writes flows with ≥2 packets (`FlowGenerator.java:94`), so single-packet traceroute probes and DNS queries are absent by design
- **`tshark -r <file in $HOME>` fails with "You don't have permission".** Ubuntu's AppArmor profile `/etc/apparmor.d/tshark` blocks tshark from reading files outside `/tmp`. Without sudo, pipe the file in: `cat f.pcap | tshark -r - ...`. To write, use `-w -` and redirect: `> out.pcap`. `capinfos` is not affected.
- **Multiclass LR needs `max_iter` ≥ 2000.** The balanced fit takes about 45 s.
- **Cache the cleaned data** to `artifacts/clean.parquet`. Unit tests use the fixture, never the 52 MB CSV.
- **Save figures as PNG (200 dpi) and PDF;** they are reused in the report.

## 8. Conventions

- Use type hints and small functions in `src/lab2ids`. Scripts are thin argparse CLIs.
- Use `random_state=42` everywhere. Log every row and column drop with its count.
- Do not create a git repo or commit unless the user asks.

---

## 9. Report (`G8.Report2.pdf`, LaTeX): everything lives in `reports/`

The full plan is `/home/aayush/.claude/plans/cheeky-herding-goose.md`, and the steps are tracked in TASKS.md P4. The template comes from Lab 1 (`../Lab1/G8_Report1_Version_2/G8_Report1_source/`).

- **Location rule (user):** ALL LaTeX/report files and folders live under `Lab2/reports/`. Nothing report-related goes in the Lab2 root. Exception: `SS/`, the user's screenshot folder, stays at `Lab2/SS/`.
- **Build: ALWAYS with `latexmkrc_2`, from inside `reports/`** (user requirement):
  ```
  cd reports && latexmk -C -r latexmkrc_2 -jobname=thesis thesis.tex && latexmk -r latexmkrc_2 -jobname=thesis thesis.tex
  ```
  - The engine is LuaLaTeX + biber. `latexmkrc_2` deletes the temporary files, including `.lol`.
  - The final deliverable is `cp reports/thesis.pdf reports/G8.Report2.pdf`.
- **Layout (`reports/`):**
  - `thesis.tex`, `latexmkrc`, `latexmkrc_2`, `bibliography.bib`, `appendix.tex`, `includes/`
  - `chapters/{introduction,task1_flows,task2_dataset,task3_preprocessing,task4_ml,task4_realtime,discussion}.tex`
  - `images/uni-logo.png`
  - `tables/*.tex`, generated by `uv run python scripts/make_report_tables.py`; the default `--out` is `reports/tables`
- **Paths from `reports/` go one level up.** TeX's `openin_any=a` allows this.
  - Figures are referenced in place: `\graphicspath{{images/}{../SS/}{../outputs/task3/figures/}{../outputs/task4/figures/}}`. Never copy them.
  - Listings use `\lstinputlisting{../src/lab2ids/...}`.
  - `\ssfig` checks `../SS/<name>.png`.
- **Numbers rule:** every metric or count in the report comes from `reports/tables/*.tex` (generated) or `HANDOVER_REPORT.md`. Never type numbers from memory or from agent transcripts.
- **Code listings** come from the real source files. Use DejaVu Sans Mono for code. `siunitx` is not installed.
- **Screenshots:** the user supplies SS15+ in `SS/` (list in the plan, R5). Until a file exists, `\ssfig` shows a "pending" box.
- **Content source:** `HANDOVER_REPORT.md`. Style follows the Lab 1 report: concise "we" prose, `booktabs` tables, descriptive captions.
- **User decisions:** cover Tasks 1–4; the dataset choice was our own (web attacks are harder to detect than volumetric DDoS); short inline code excerpts; same authors as Lab 1. The main matter must be 10–15 pages.
