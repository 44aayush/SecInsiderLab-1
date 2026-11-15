# CLAUDE.md: Security Insider Lab, Lab 3 (Training ML and DL models for DDoS detection)

Lab 3 trains 5 classical classifiers (Task 1) and 3 neural networks (Task 2) on the CIC-IDS2017 Friday DDoS flow file, then compares all 8 models (Task 3). Task 4 and the deck-only Task 5 (eBPF/XDP filtering) are planned in `TASKS.md` P7 and start only after Tasks 1–3 are done (user decision D2).

- Course: Security Insider Lab, Uni Passau, group **G8** (max 2 members per group).
- Specs: `Task1.png` … `Task4.png` in this folder, which are slides 7–10 of `Security_Insider_lab_3.pptx`. Slide 11 adds a **Task 5** (xdp-tools) that is not in the PNGs. Progress is tracked in `TASKS.md`.
- Deadlines (deck slides 5 and 12): the report `G8.Report3.pdf` was due **2026-11-11**, which had already passed on 2026-11-13. The presentation is on **2026-11-25**. Details are in §10.
- **Scope rule:** build what the specs and the user's decisions (§2) ask for, plus the tests needed to trust the results. Do not add tasks, features, models or demos without the user's approval.
- **Self-contained:** Lab 3 never imports from `../Lab2`. Porting verified Lab 2 logic (copy and adapt) is allowed and encouraged; name the source file in the module docstring.
- **Task work starts only when the user prompts.** The user reviews these docs first.

---

## 1. Model routing (MANDATORY, user instruction 2026-11-13)

| Work type | Model | How to delegate |
|---|---|---|
| Orchestration, planning, analysis of the task specs, design decisions, audit and review of code and outputs, **writing and maintaining this `CLAUDE.md` and `TASKS.md`** | **Opus 5.5** (main session) | inline |
| Review of `CLAUDE.md` and `TASKS.md` | **Fable 5.2** | `Agent(subagent_type="general-purpose", model="fable", ...)`, read-only; returns findings, and Opus applies them |
| Coding: Python modules, unit and e2e tests, debugging, pylint fixes. Future docs (README, report text), LaTeX, presentation | **Sonnet 5.5** | `Agent(subagent_type="general-purpose", model="sonnet", ...)` |
| Browser use, command-line execution (env setup, running `main.py`/`pytest`/`pylint`/`radon`, collecting output), file inventory, text extraction, other low-level tasks | **Haiku 5.5** | `Agent(subagent_type="general-purpose", model="haiku", ...)` |

Rules:

1. **Exception to the global routing** (user, 2026-11-13): the Lab 3 `CLAUDE.md` and `TASKS.md` are written by Opus and reviewed by Fable. Every other document goes to Sonnet.
2. Subagents start cold. Each prompt names the `TASKS.md` ID(s), tells the agent to read this file and its `TASKS.md` entry first, and gives the exact output paths and the AC.
3. Sonnet may run `pytest`, `pylint`, `radon` and short smoke runs while debugging its own code. This is Opus's interpretation of the routing: "debugging" is Sonnet's work. Env setup, the full `main.py` run, the e2e tests and the official verification runs stay with Haiku.
4. Haiku reports output verbatim and edits no files. Running commands may create `.venv/`, caches and `outputs/`. Opus routes every fix to Sonnet.
5. Opus checks each result against its AC and §3, then ticks the box in `TASKS.md`. **Only Opus ticks boxes.**
6. `sudo` is not available non-interactively. The user runs every root step personally (apt installs, XDP attach); give the exact commands (see `TASKS.md` T7.0).

---

## 2. Specs and user decisions

| Task | Spec (PNG / slide) | What is built |
|---|---|---|
| 1 | "Apply 5 different classifiers; select by yourself or go with: Gaussian NB, Gradient Boosting, AdaBoost, KNN, SVM" (`Task1.png`, slide 7) | **User's choice:** Gaussian Naive Bayes, Logistic Regression, KNN, Random Forest, XGBoost. One file each, in `script/clf/`. |
| 2 | "Apply Multi Layer Perceptron, LSTM, CNN" (`Task2.png`, slide 8) | PyTorch (CPU), in `script/dl/`: `mlp_dl.py`, `lstm_dl.py`, `cnn_dl.py` |
| 3 | "Generate comparison table; compare Accuracy, F-score, Precision and Recall; compare and draw ROC curves" (`Task3.png`, slide 9) | In `script/`: `comparison.py` (tables, figure index), `plots_metrics.py`, `plots_confusion.py`, `plots_training.py`, `roc_curves.py` |
| 4 | eBPF/XDP theory: what it is, use cases, available tools discussed briefly; write a small XDP filter program (`Task4.png`, slide 10) | Planned, `TASKS.md` P7. Starts after Tasks 1–3 (D2). |
| 5 | Deck only (slide 11): download and configure `github.com/xdp-project/xdp-tools`; may slip to the Lab 4 deadline | Planned, `TASKS.md` P7 |

Binding user instructions (2026-11-13):

- Dataset: `Friday-WorkingHours-Afternoon-DDos.csv` (in this folder).
- `preprocess.py` removes inf values, NaN values, constant columns and identical columns. **D1:** it also removes duplicate rows.
- One Python file per classifier and per DL model. `main.py` calls preprocess → classifiers → `*_dl.py` → the comparison file(s).
- **D5 Layout:** every Python module lives under `script/`. The classifiers are in `script/clf/` and the DL models in `script/dl/` (§4.1, §6).
- Split: **70 % train / 15 % validation / 15 % test**.
- Every function has at most **medium** complexity (§8).
- Use pylint, uv and a venv. List every package in `requirements.txt`.
- Comment every piece of functionality (§8).
- **D2:** Tasks 4–5 come after Tasks 1–3, and the user installs the toolchain personally.
- **D3:** the report and the presentation are deferred; keep the §10 structure.
- **D4:** keep all the extra comparison outputs (§4.11 metrics, the val table, md/tex exports), and generate **several chart and grid variants** (§5.1). The user picks figures from `outputs/figures/INDEX.md`, and the report and the deck reuse that selection.

- **D6 (2026-11-13):** `WINDOWS.md` for running on Windows with an RTX 3050 6 GB (`--device cuda`); a `--log-txt` report; TP and TN columns. **Per-model DL epoch limits** (MLP 30, CNN 30, LSTM 15) were chosen by experiment, under the user's rule that a longer limit is adopted only if no test metric gets worse. At 30 epochs MLP and CNN improved on every metric; the LSTM's precision and FP got worse, so it stayed at 15. **Superseded for the LSTM on 2026-11-15 (D7).**
- **D7 (2026-11-15, user):** the LSTM gets gradient clipping 1.0, its own learning rate and patience. Values chosen by Opus by lowest **validation** loss over a 3-config grid (Linux CPU): lr 5e-4 / patience 7 / cap 40 (val loss 0.00529) beat lr 5e-4 / p5 / cap 30 (0.00567, hit the cap) and lr 3e-4 / p5 / cap 40 (0.00720). Settings live in `dl/lstm_dl.py` (`LEARNING_RATE`, `PATIENCE`, `MAX_EPOCHS`, `GRAD_CLIP_NORM`) and reach `run_dl` as `dl_common.TrainSettings`; MLP and CNN keep the shared lr 1e-3, patience 3, no clipping.

The Task 1 slide names Gradient Boosting, AdaBoost and SVM but allows an own selection. LR, RF and XGBoost are the user's choice; the report states this.

---

## 3. Verified data facts

Lab 2 profiled this file on 2026-11-09 (`../Lab2/Friday_Dataset/CLAUDE.md` §2). Fable re-ran the §4.4 cleaning on the **Lab 3 copy** on 2026-11-13 (Lab 3 venv: pandas 3.1.0, sklearn 1.9.1), and every number below reproduced.

Both copies have sha256 `646fd1282cf584bd330caf4dab51c689799b223425cf643edde172a1a655793d` (77,349,605 bytes, about 77 MB). The Lab 3 e2e test (T5.7) pins these numbers on the Lab 3 code.

- **Raw:** 225,745 rows × 79 columns (78 features + `Label`). All features are numeric. CRLF line endings, pure ASCII, no blank lines.
  - 65 header names have stray spaces, so strip all names.
  - `Fwd Header Length` appears twice. pandas renames the second copy `Fwd Header Length.1`; it is an exact copy.
- **Labels:** DDoS 128,027 (56.7 %, the majority class), BENIGN 97,718. Labels are clean (no U+FFFD).
- **inf/NaN** (all +inf, no −inf): `Flow Bytes/s` has 30 inf and 4 NaN; `Flow Packets/s` has 34 inf. In total **34 rows** are affected: 32 BENIGN, 2 DDoS.
- **Duplicate rows**, counted after the inf/NaN drop on the full row including `Label`: **2,629** (2,618 BENIGN, 11 DDoS). There are 2,633 in the raw file.
- **Constant columns: 10**, exactly the list in `../Lab2/Friday_Dataset/tests/test_task3.py:174-177`.
- **Identical columns: 9 dropped.** These are the 8 in `test_task3.py:178-180` plus `Fwd Header Length.1`, which pairs with `Fwd Header Length`. The first occurrence of each pair is kept. `Avg Bwd Segment Size` is the only twin that is not an exact copy: it differs in 2 rows by less than 1e-6, so the check needs `atol=1e-6`.
- **Clean set:** **223,082 rows × 59 features** (78 − 10 − 9). DDoS 128,014, BENIGN 95,068. Dropping the columns creates no new duplicate rows.
- **Negative values** exist (`Init_Win_bytes_*` = −1, and a few IAT/duration values).
- **Destination Port shortcut:** DDoS flows are almost all dst port 80 (128,011 of 128,014). In Lab 2 the decision tree gave this feature an importance of 0.35. It is kept and reported honestly; no ablation is done (scope).
- **70/15/15 split** (two-stage stratified split, seed 42; verified):

  | Split | Rows | DDoS | BENIGN |
  |---|---:|---:|---:|
  | train | 156,157 | 89,610 | 66,547 |
  | val | 33,462 | 19,202 | 14,260 |
  | test | 33,463 | 19,202 | 14,261 |

- **Lab 2 baselines** (70/30, MinMax + chi2 top-20, so not directly comparable): Decision Tree DDoS-F1 0.9996, Logistic Regression ≈ 0.974. Expect near-perfect scores for RF, XGB and the DL models. The differences will show in the FP/FN counts.
- **Fixture** `../Lab2/Friday_Dataset/tests/fixtures/sample_ddos.csv`: 3,187 rows (1,665 BENIGN / 1,522 DDoS), with 34 inf rows.

### Final results (test split, 2026-11-13, Linux CPU; `outputs/run_report.txt`, metrics files as of commit afa8747)

| Model | Acc | Prec | Rec | F1 | ROC-AUC | TP | TN | FP | FN |
|---|---|---|---|---|---|---|---|---|---|
| XGBoost | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 19202 | 14261 | 0 | 0 |
| Random Forest | 0.9999 | 1.0000 | 0.9998 | 0.9999 | 1.0000 | 19199 | 14261 | 0 | 3 |
| KNN | 0.9998 | 0.9999 | 0.9997 | 0.9998 | 0.9999 | 19197 | 14260 | 1 | 5 |
| MLP | 0.9995 | 0.9997 | 0.9994 | 0.9995 | 1.0000 | 19190 | 14255 | 6 | 12 |
| 1D-CNN | 0.9990 | 0.9993 | 0.9990 | 0.9991 | 1.0000 | 19182 | 14248 | 13 | 20 |
| Logistic Regression | 0.9980 | 0.9977 | 0.9988 | 0.9983 | 0.9999 | 19179 | 14217 | 44 | 23 |
| LSTM | 0.9935 | 0.9947 | 0.9939 | 0.9943 | 0.9998 | 19084 | 14160 | 101 | 118 |
| Gaussian NB | 0.9895 | 0.9832 | 0.9986 | 0.9909 | 0.9880 | 19176 | 13934 | 327 | 26 |

### Windows GPU run (test split, 2026-11-15; RTX 3050 6 GB Laptop, torch 2.15.0+cu132, 16 threads; `outputs/run_report_windows.txt`, current `outputs/metrics/*`)

Same CSV sha256, same preprocessing and split counts. Only the rows that differ from the CPU table:

| Model | Acc | Prec | Rec | F1 | ROC-AUC | TP | TN | FP | FN | vs CPU |
|---|---|---|---|---|---|---|---|---|---|---|
| MLP | 0.9995 | 0.9996 | 0.9995 | 0.9996 | 1.0000 | 19193 | 14254 | 7 | 9 | F1 +0.0001; FP +1, FN −3 |
| 1D-CNN | 0.9993 | 0.9997 | 0.9990 | 0.9993 | 1.0000 | 19183 | 14255 | 6 | 19 | better on every metric (FP 13→6) |
| Logistic Regression | 0.9981 | 0.9979 | 0.9988 | 0.9983 | 0.9999 | 19179 | 14220 | 41 | 23 | FP 44→41 (BLAS numerics) |
| LSTM | 0.9866 | 0.9781 | 0.9991 | 0.9885 | 0.9986 | 19185 | 13831 | 430 | 17 | **worse**: early-stopped at epoch 7 (best 4) after a loss spike |

GNB, KNN, RF and XGBoost are identical. Opus analysis: §9 "Cross-platform".

### LSTM runs (test split; LSTM-only runs, own output folders)

| Run | Settings | Acc | Prec | Rec | F1 | ROC-AUC | FP | FN | Best / stop epoch |
|---|---|---|---|---|---|---|---|---|---|
| Linux CPU, `outputs/run.log` (2026-11-13) | lr 1e-3, p3, cap 15, no clip | 0.9935 | 0.9947 | 0.9939 | 0.9943 | 0.9998 | 101 | 118 | 14 / 15 |
| Windows GPU, `outputs/` (2026-11-15) | same | 0.9866 | 0.9781 | 0.9991 | 0.9885 | 0.9986 | 430 | 17 | 4 / 7 |
| Linux CPU, `outputs_lstm_clip_linux_cpu/` | + clip 1.0 | 0.9958 | 0.9940 | 0.9988 | 0.9964 | 0.9998 | 116 | 23 | 12 / 15 |
| **Linux CPU, `outputs_lstm_enhance_linux_cpu/` (final, D7)** | lr 5e-4, p7, cap 40, clip 1.0 | **0.9990** | **0.9992** | **0.9992** | **0.9992** | **1.0000** | **16** | **16** | 31 / 38 |

The D7 LSTM is better than every earlier LSTM on every test metric, and it now ranks between MLP (F1 0.9995) and 1D-CNN (0.9991). Training takes 137 s on CPU. `outputs/` still holds the old LSTM; re-run the full pipeline before the report to get consistent 8-model tables and figures.

---

## 4. Design decisions

1. **Layout (D5):** all Python code is under `Lab3/script/`.
   - `script/` holds `main.py` and the shared modules: `common`, `preprocess`, `evaluate`, `comparison`, `plots_*` and `roc_curves`.
   - `script/clf/` holds `ml_common.py` and the 5 `*_clf.py` files. `script/dl/` holds `dl_common.py` and the 3 `*_dl.py` files. Both are packages (`__init__.py`).
   - **Imports:** `script/` is the import root. Run the code as `python script/main.py`; Python then puts `script/` on `sys.path`, so `import common` and `from clf import gnb_clf` work. Inside the packages, use `import common` and `from clf.ml_common import run_sklearn` (or `from dl.dl_common import ...`).
   - There is no package install. Tests use `pythonpath = script` in `pytest.ini`, and pylint uses `source-roots=script` in `.pylintrc`.
2. **Environment.**
   - Python: uv-managed CPython **3.12** (`.python-version`). The system Python is 3.14; do not use it.
   - venv: `.venv`, created with `uv venv`. Packages are installed with `uv pip install -r requirements.txt --torch-backend=cpu`.
   - `requirements.txt` pins every direct dependency with `==` and groups them with comments (data/ML, DL, reporting, dev tools).
   - The data-stack pins reuse Lab 2's verified set (numpy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1, matplotlib 3.11.2). The others are pinned to what T1.1 resolved on 2026-11-13: torch 2.15.0 (installed as `2.15.0+cpu`), xgboost 3.4.1, tabulate 0.10.0, jinja2 3.1.6, pylint 4.1.3, pytest 9.2.0, radon 6.0.1. The `.venv` is 1.5 GB.
   - No `pyproject.toml`, so uv stays out of project mode. Tool config lives in `.pylintrc` and `pytest.ini`.
   - git: `outputs/` is **tracked**, because the report and the deck reuse it. `.gitignore` covers `.venv/`, the caches and the LibreOffice lock files.
3. **DL framework: PyTorch, CPU build.** The machine has no GPU (6 cores, 15 GiB RAM).
4. **Cleaning.** `preprocess.load_raw` does step 1 and `preprocess.clean(df)` does steps 2–6:
   1. load, strip column names and label values
   2. replace ±inf with NaN
   3. drop NaN rows
   4. drop duplicate rows: `df.duplicated()` on the full row including `Label` (as in Lab 2 `data.py:141`); only if `common.DROP_DUPLICATES`
   5. drop constant columns (`nunique(dropna=False) <= 1`)
   6. drop identical columns (`np.allclose(a, b, rtol=0, atol=1e-6)`; keep the first occurrence in CSV column order)

   Each step logs the rows or columns it dropped, with counts (per class for rows) and names (for columns).
   - The logic is ported from `../Lab2/Friday_Dataset/src/ddosids/data.py`; `features.py` there is chi2 selection, which §4.7 excludes.
   - **Deviation from Lab 2:** `Fwd Header Length.1` is not dropped by name up front (Lab 2 `data.py:111-115`). Step 6 catches it, and Fable verified that the rows and columns come out the same.
   - **Step 4 is confirmed by the user (decision D1, 2026-11-13).** Without it, duplicates would sit in both train and test and inflate the scores.
   - `clean` reads the flag at call time (`import common`, then `common.DROP_DUPLICATES`), so tests can monkeypatch it.
   - Steps 5 and 6 look only at feature columns, never at `Label`. They run on the full cleaned data before the split, as in Lab 2; they use no labels.
5. **Labels:** binary. `BENIGN` → 0, `DDoS` → 1; the positive class is DDoS. Any other label value raises `ValueError`.
6. **Split:** two-stage stratified `train_test_split` with `random_state=42`. First 70 % train / 30 % temp, then temp 50/50 → val / test. The indices are disjoint.
7. **Scaling:** `StandardScaler` fitted on **train only**, then applied to val and test. Arrays are cast to `float32`.
   - All 8 models get the same scaled arrays. Trees and GNB do not need scaling but are not hurt by it, and a single data path keeps `main.py` simple.
   - No feature selection (not asked for).
8. **Use of the validation set:**
   - XGBoost: early stopping (`early_stopping_rounds=20` on val logloss).
   - DL models: early stopping on val loss (patience 3), restoring the best weights.
   - Val metrics are reported for every model. For the early-stopped models (XGB, MLP, LSTM, CNN) the val scores are **selection-biased** (optimistic); the test scores are the unbiased figures.
   - There is no hyper-parameter search (not asked for).
   - The test set is used **once**, for the final tables and figures.
9. **Hyper-parameters** (fixed; module-level constants in each model file):

   | Key | Model |
   |---|---|
   | `gnb` | `GaussianNB()` with defaults |
   | `lr` | `LogisticRegression(max_iter=2000, random_state=42)` |
   | `knn` | `KNeighborsClassifier(n_neighbors=5, n_jobs=-1)` |
   | `rf` | `RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42)` |
   | `xgb` | `XGBClassifier(n_estimators=500, max_depth=6, learning_rate=0.1, tree_method="hist", eval_metric="logloss", early_stopping_rounds=20, n_jobs=-1, random_state=42)`. `run` passes `fit_kwargs={"eval_set": [(x_val, y_val)], "verbose": False}`; `fit` defaults to `verbose=True`, which prints one line per round. |
   | `mlp` | n_features → 128 → 64 → 1; ReLU, Dropout 0.2 |
   | `lstm` | input reshaped to (batch, n_features, 1); `nn.LSTM(input_size=1, hidden_size=32, batch_first=True)`; `h_n[-1]` → Linear(32 → 1). `batch_first=True` is required: without it the batch is read as time steps. Own settings (D7): lr 5e-4, patience 7, max 40 epochs, gradient-norm clipping 1.0. |
   | `cnn` | input reshaped to (batch, 1, n_features); Conv1d(1→32, k=3, pad=1) + ReLU + MaxPool1d(2) → Conv1d(32→64, k=3, pad=1) + ReLU → AdaptiveMaxPool1d(1) → Linear(64 → 1). Needs n_features ≥ 2. |

   - **DL models:** each `nn.Module` takes `n_features: int` in its constructor, and `run` passes `splits.x_train.shape[1]`. Each model reshapes its input inside `forward()`, so all DL models take the same 2-D float32 arrays.
   - **Shared DL settings:** the numeric constants live in `common.py` (batch 1024, lr 1e-3, max 15 epochs, patience 3, `SEED`). `dl_common.py` creates the loss (`BCEWithLogitsLoss`) and the optimiser (Adam). `common.py` never imports torch.
   - **Seeding:** each `*_dl.run` calls `dl_common.set_seed(SEED)` (torch, numpy, `random`) **before** it instantiates its model. `run_dl` does not re-seed. The DataLoader shuffles with a generator seeded with `SEED`.
10. **Prediction rule:** every model outputs P(DDoS) as its score. `y_pred = (score > 0.5)`, which is the same tie-break as sklearn's `predict` (an exact 0.5 → BENIGN). Fable verified that this equals `predict` for all 5 classifiers.
11. **Metrics** (val and test, DDoS as the positive class, `zero_division=0`):
    - Accuracy, Precision, Recall, F1, macro-F1 and ROC-AUC
    - the confusion matrix `[[TN, FP], [FN, TP]]`
    - train time (s) and test predict time (s)

    **Never report accuracy alone.** All of them are kept (D4).
12. **Figures** (D4: several variants; the user picks):
    - Use matplotlib's object-oriented API: `matplotlib.figure.Figure()` and `fig.add_subplot(...)`, including `projection="polar"` for the radar chart. **Never import `matplotlib.pyplot`.** This avoids GUI backends in Haiku and pytest runs and the global figure state, and needs no `matplotlib.use()` import-order hack.
    - `common.save_figure` writes PNG (200 dpi) and PDF.
    - Use one fixed colour per model, from `common.MODEL_COLORS`: the Okabe–Ito colour-blind-safe palette, with yellow replaced by grey for contrast. ML models are drawn with solid lines and DL models with dashed ones.
    - Every plot function works for **any number of models ≥ 1**, because smoke runs use 3. Grids use 4 columns and `ceil(n / 4)` rows. A figure whose model set is empty (for example `roc_test_dl` without DL models) is skipped with a log line.
    - The catalog is in §5.1. `comparison.write_figure_index` writes `outputs/figures/INDEX.md`, which lists every generated figure with its chart type and purpose and links the PNG, so the user can choose.
13. **Logging:** `logging` to the console and to `outputs/run.log`, opened with mode `"w"`. `setup_logging` removes and closes any existing root handlers first, so it is safe to call twice (the tests call `main()` in-process). Modules never call `print`.
14. **Lazy model imports:** `main.py` maps each key to a module name (`clf.gnb_clf`, …, `dl.cnn_dl`) and imports it with `importlib`, so `--models gnb lr` never imports torch.

---

## 5. Module contract (Sonnet must follow it exactly; the tests rely on it)

```python
# script/common.py  (never imports torch)
LAB3_DIR = Path(__file__).resolve().parents[1]         # common.py lives in Lab3/script/
DEFAULT_CSV = LAB3_DIR / "Friday-WorkingHours-Afternoon-DDos.csv"
DEFAULT_OUT = LAB3_DIR / "outputs"
SEED = 42
TRAIN_FRAC, VAL_FRAC, TEST_FRAC = 0.70, 0.15, 0.15
NEGATIVE_LABEL, POSITIVE_LABEL = "BENIGN", "DDoS"      # encoded 0 / 1
DROP_DUPLICATES = True
IDENTICAL_ATOL = 1e-6
DL_BATCH_SIZE, DL_LR, DL_DEFAULT_MAX_EPOCHS, DL_PATIENCE = 1024, 1e-3, 15, 3   # per-model MAX_EPOCHS in dl/*_dl.py (D6)
FIG_DPI = 200
MODEL_COLORS = {"gnb": "#E69F00", "lr": "#56B4E9", "knn": "#009E73", "rf": "#0072B2",
                "xgb": "#D55E00", "mlp": "#CC79A7", "lstm": "#000000", "cnn": "#7F7F7F"}

@dataclass(frozen=True)
class DataSplits:
    x_train: np.ndarray        # float32 (n, f), scaled
    x_val: np.ndarray
    x_test: np.ndarray
    y_train: np.ndarray        # int64 (n,), 1 = DDoS
    y_val: np.ndarray
    y_test: np.ndarray
    feature_names: list[str]

@dataclass
class ModelResult:             # 8 fields: .pylintrc sets max-attributes=8 (§8)
    key: str                   # registry key, e.g. "rf"
    name: str                  # display name, e.g. "Random Forest"
    family: str                # "ML" or "DL"
    y_val_score: np.ndarray    # P(DDoS) on val, floats in [0, 1]
    y_test_score: np.ndarray   # P(DDoS) on test
    train_time_s: float
    predict_time_s: float      # test set only
    history: dict[str, list[float]] | None = None   # DL: {"train_loss": [...], "val_loss": [...]}

def setup_logging(out_dir: Path) -> None: ...          # idempotent; console + out_dir/run.log (mode "w")
def save_figure(fig: Figure, stem: Path) -> None: ...  # stem.png (FIG_DPI) + stem.pdf; creates the parent dir
```

The best epoch is `argmin(history["val_loss"])`, which is the epoch whose weights `EarlyStopper` restores. It is derived, not stored.

| Module | Public API |
|---|---|
| `preprocess.py` | `load_raw(csv_path) -> pd.DataFrame` (step 1), `clean(df) -> tuple[pd.DataFrame, dict]` (steps 2–6, plus their part of the summary), `encode_labels`, `split_data`, `scale_splits`, and `preprocess(csv_path: Path) -> tuple[DataSplits, dict]` (runs them all and returns the full summary below) |
| `clf/ml_common.py` | `run_sklearn(model, key: str, name: str, splits: DataSplits, fit_kwargs: dict \| None = None) -> ModelResult`: times the fit and the test predict, and returns `predict_proba[:, 1]` for val and test |
| `clf/*_clf.py` | `KEY`, `NAME`, `build_model()`, `run(splits) -> ModelResult` (family `"ML"`) |
| `dl/dl_common.py` | `set_seed(seed)`; `make_loader(x, y, shuffle) -> DataLoader`; `class EarlyStopper(patience)` with `update(val_loss: float, model) -> bool` (True means stop; deep-copies the best `state_dict`) and `restore(model)`; `train_model(model, splits, max_epochs) -> dict` (the history; uses `EarlyStopper`; restores the best weights); `predict_scores(model, x) -> np.ndarray` (sigmoid; batched; eval mode; `no_grad`); `make_step(model, optimizer, grad_clip_norm)` (optional `clip_grad_norm_`, then `optimizer.step()`); `TrainSettings(lr, patience, grad_clip_norm)` (frozen; defaults = the shared `common` values, no clipping); `run_dl(model, key, name, splits, max_epochs, device="cpu", settings=None) -> ModelResult` |
| `dl/*_dl.py` | `KEY`, `NAME`, one `nn.Module` subclass `__init__(self, n_features: int)`, `run(splits, max_epochs: int = DL_MAX_EPOCHS) -> ModelResult` (family `"DL"`; seeds before building the model) |
| `evaluate.py` | `compute_metrics(y_true, y_score) -> dict`; `evaluate_all(results: list[ModelResult], splits) -> dict` (schemas below) |
| `comparison.py` | `FIGURE_CATALOG` (stem → (chart type, purpose), §5.1); `build_table(metrics, split) -> pd.DataFrame`; `save_table(df, metrics_dir, stem)` (csv/md/tex); `plot_table_image(df, fig_dir)`; `run_comparison(results, metrics, out_dir)` (tables, then `plots_metrics`, `plots_confusion` and `plots_training`); `write_figure_index(out_dir)` |
| `plots_metrics.py` | `plot_all(metrics, fig_dir)`, plus one small function per metric chart of §5.1 |
| `plots_confusion.py` | `plot_all(metrics, fig_dir)`, covering the grids and the per-model matrices |
| `plots_training.py` | `plot_all(results, fig_dir)`; skipped with a log line when no result has a `history` |
| `roc_curves.py` | `plot_roc(results: list[ModelResult], y_test: np.ndarray, out_dir)`, which writes the 6 ROC stems of §5.1 |
| `main.py` | `main(argv: list[str] \| None = None) -> int`. CLI options: `--csv`, `--out`, `--models` (a subset of the keys below; default all, in this order), `--epochs N` (overrides every DL model's `MAX_EPOCHS`; default None = per-model limits), `--device {auto,cpu,cuda}` (DL only; auto = cuda if available), `--log-txt PATH` (one self-contained text report to share with an LLM; built by `run_report.py`) |

**Directory arguments.** Every `out_dir` is the `--out` root; those functions create `metrics/` and `figures/` themselves. The helper modules (`plots_*`, `plot_table_image`) take `fig_dir = out_dir / "figures"` explicitly. `results` is always a `list[ModelResult]` in run order.

**Preprocess summary** (`outputs/metrics/preprocess_summary.json`). The values shown are the expected full-CSV values from §3. Everything is JSON-serialisable (plain int/float/str/list/dict), and the `by_class` and class-count dicts use the keys `"BENIGN"` and `"DDoS"`.

```python
{
  "raw_shape": [225745, 79],                                    # rows, columns incl. Label
  "raw_class_counts": {"BENIGN": 97718, "DDoS": 128027},
  "inf_counts": {"Flow Bytes/s": 30, "Flow Packets/s": 34},     # ±inf per column, only columns > 0
  "nan_counts": {"Flow Bytes/s": 4},                            # NaN already in the raw file, only columns > 0
  "inf_nan_rows": {"n": 34, "by_class": {"BENIGN": 32, "DDoS": 2}},
  "duplicate_rows": {"n": 2629, "by_class": {"BENIGN": 2618, "DDoS": 11}},  # n = 0 if DROP_DUPLICATES is False
  "constant_columns": ["<10 names>"],
  "identical_columns": {"<dropped>": "<kept twin>"},            # 9 entries
  "clean_shape": [223082, 59],                                  # rows, feature columns (Label excluded)
  "clean_class_counts": {"BENIGN": 95068, "DDoS": 128014},
  "split_sizes": {"train": 156157, "val": 33462, "test": 33463},
  "split_class_counts": {"train": {"BENIGN": 66547, "DDoS": 89610},
                         "val": {"BENIGN": 14260, "DDoS": 19202},
                         "test": {"BENIGN": 14261, "DDoS": 19202}},
  "feature_names": ["<59 names>"]
}
```

**Metrics** (`outputs/metrics/metrics.json`), JSON-serialisable:

```python
compute_metrics(y_true, y_score) -> {"accuracy": float, "precision": float, "recall": float, "f1": float,
                                     "macro_f1": float, "roc_auc": float, "tn": int, "fp": int, "fn": int, "tp": int}
evaluate_all(results, splits) -> {"<key>": {"name": str, "family": "ML" | "DL",
                                            "val": {...compute_metrics...}, "test": {...compute_metrics...},
                                            "train_time_s": float, "predict_time_s": float}}   # dict order = run order
```

**Comparison table** (`comparison_{test,val}.{csv,md,tex}` and the `comparison_table` image): the columns are Model, Family, Accuracy, Precision, Recall, F1, Macro-F1, ROC-AUC, TP, TN, FP, FN, Train time (s), Predict time (s) (TP/TN added by D6). Scores have 4 decimals (user: decimals, not %); times have 3. Rows are sorted by F1, descending; the metrics have 4 decimals.

All module paths in this table are relative to `script/`.

| Key | File (import name) | Display name | Family |
|---|---|---|---|
| `gnb` | `clf/gnb_clf.py` (`clf.gnb_clf`) | Gaussian Naive Bayes | ML |
| `lr` | `clf/lr_clf.py` (`clf.lr_clf`) | Logistic Regression | ML |
| `knn` | `clf/knn_clf.py` (`clf.knn_clf`) | K-Nearest Neighbors | ML |
| `rf` | `clf/rf_clf.py` (`clf.rf_clf`) | Random Forest | ML |
| `xgb` | `clf/xgb_clf.py` (`clf.xgb_clf`) | XGBoost | ML |
| `mlp` | `dl/mlp_dl.py` (`dl.mlp_dl`) | MLP | DL |
| `lstm` | `dl/lstm_dl.py` (`dl.lstm_dl`) | LSTM | DL |
| `cnn` | `dl/cnn_dl.py` (`dl.cnn_dl`) | 1D-CNN | DL |

### 5.1 Figure catalog (D4: all on the test split; each stem is written as `.png` and `.pdf`)

| Stem | Module | Chart type | Purpose |
|---|---|---|---|
| `metrics_bar_grouped` | plots_metrics | grouped vertical bars, y-axis starting just below the lowest value | Accuracy, Precision, Recall and F1 per model |
| `metrics_small_multiples` | plots_metrics | 2×2 grid of sorted horizontal bars, one panel per metric | ranking per metric |
| `metrics_heatmap` | plots_metrics | annotated heatmap, models × the 6 scores | everything at a glance |
| `metrics_radar` | plots_metrics | radar (spider) chart, one polygon per model, radial axis zoomed | the profile of each model |
| `metrics_dot` | plots_metrics | Cleveland dot plot, one row per model, one marker per metric | a compact comparison |
| `errors_bar` | plots_metrics | grouped bars of FP and FN per model, log y-axis | where the near-perfect models really differ |
| `time_bar` | plots_metrics | horizontal bars of train and predict time, log x-axis | cost |
| `comparison_table` | comparison | the test table rendered as an image | a slide-ready table |
| `confusion_grid_counts` | plots_confusion | grid of confusion heatmaps, raw counts | all models side by side |
| `confusion_grid_normalized` | plots_confusion | the same grid, row-normalised rates (4 decimals) | rates instead of counts |
| `confusion_<key>` | plots_confusion | a single confusion heatmap per model run | one model on one slide |
| `roc_test` | roc_curves | all models, full axes, chance diagonal, AUC in the legend | the Task 3 ROC figure |
| `roc_test_zoom` | roc_curves | FPR 0–0.05, TPR 0.95–1.0 | separates the near-perfect models |
| `roc_test_logx` | roc_curves | log-scale FPR (1e-5 to 1; FPR 0 is clipped) | low false-alarm behaviour |
| `roc_grid` | roc_curves | small multiples, one model per panel, with its AUC | each curve on its own |
| `roc_test_ml`, `roc_test_dl` | roc_curves | ML-only and DL-only overlays | the family comparison |
| `dl_history_overlay` | plots_training | val loss of all DL models on one axis | convergence compared |
| `dl_history_grid` | plots_training | one panel per DL model: train and val loss, best epoch marked | early stopping shown |

`INDEX.md` lists only the stems that exist after a run. For the full 8-model run that is 26 stems (8 of them `confusion_<key>`).

---

## 6. Layout

```
Lab3/
├── CLAUDE.md  TASKS.md                                   # Opus-owned, Fable-reviewed
├── Task1.png … Task4.png  Security_Insider_lab_3.pptx    # specs (read-only)
├── Friday-WorkingHours-Afternoon-DDos.csv                # dataset (read-only, 77 MB)
├── requirements.txt  .python-version  .pylintrc  pytest.ini  .gitignore
├── script/                                               # all Python code (D5); the import root
│   ├── main.py                                           # entry point: Tasks 1–3
│   ├── common.py                                         # constants, dataclasses, logging, save_figure
│   ├── preprocess.py                                     # cleaning, 70/15/15 split, scaling
│   ├── evaluate.py  comparison.py  plots_metrics.py  plots_confusion.py  plots_training.py  roc_curves.py   # Task 3
│   ├── clf/   __init__.py  ml_common.py  gnb_clf.py  lr_clf.py  knn_clf.py  rf_clf.py  xgb_clf.py      # Task 1
│   └── dl/    __init__.py  dl_common.py  mlp_dl.py  lstm_dl.py  cnn_dl.py                            # Task 2
├── tests/    conftest.py  fixtures/sample_ddos.csv  test_*.py
├── outputs/  GENERATED, tracked (see below)
└── xdp/      Tasks 4–5 (planned, P7)
```

Generated by `python script/main.py`:

```
outputs/
├── run.log
├── metrics/   preprocess_summary.json  metrics.json  comparison_test.{csv,md,tex}  comparison_val.{csv,md,tex}
└── figures/   INDEX.md  plus every §5.1 stem as .png and .pdf
```

---

## 7. Commands

Run from `Lab3/`.

```bash
cd /home/aayush/Desktop/SecInsiderLab1/SecInsiderLab-1/Lab3
uv venv --python 3.12 .venv                                                   # once
uv pip install --python .venv/bin/python -r requirements.txt --torch-backend=cpu
source .venv/bin/activate                                                     # or prefix commands with .venv/bin/
python script/main.py                                                         # all 8 models on the full CSV (about 5 min on CPU; add --device cuda --log-txt outputs/run_report.txt as needed)
python script/main.py --models gnb lr rf                                      # subset; does not import torch
python script/main.py --csv tests/fixtures/sample_ddos.csv --epochs 1 --out "$(mktemp -d)"   # smoke run, < 1 min
pylint script tests                                                           # must be 10.00/10 (recursive and source-roots are set in .pylintrc)
radon cc -s -a script tests                                                   # complexity report (grades A–B only)
radon cc -n C script tests                                                    # must print nothing
pytest -m "not e2e" -q                                                        # unit tests, < 120 s
pytest -m e2e -q                                                              # full CSV; pins §3
```

---

## 8. Code-quality rules

- **Complexity: "max medium" (user rule).** This is interpreted conservatively: every function and method has a McCabe complexity of **≤ 10** (radon grades A–B), which satisfies "max medium" under any reading. Radon calls grade C (11–20) "moderate", and it is not allowed. This is enforced by:
  - pylint's `pylint.extensions.mccabe` with `max-complexity=10`
  - `radon cc -n C`, which must print nothing
  - pylint's default design limits (args 5, locals 15, branches 12, statements 50), with one documented exception: `max-attributes=8` for the 8-field `ModelResult` contract (§5)

  Keep each module under about 200 lines; split it if it grows past that.
- **pylint 10.00/10** on `script tests`. Every disable, in `.pylintrc` or inline, carries a one-line reason comment. Fix torch `no-member` false positives with `generated-members`, never by disabling E1101 globally. `good-names` may add `x`, `y`, `df`, `ax`, `fig`.
- **Comments for each functionality (user rule):**
  - a module docstring: the module's purpose, which Task it serves and, for ported code, its Lab 2 source
  - a Google-style docstring (summary, Args, Returns, Raises) on every function, method and class, including private ones
  - inline comments on every non-obvious step, saying why rather than what
- Type hints on every signature.
- No magic numbers: hyper-parameters are module-level constants, and shared ones live in `common.py`. `SEED` is used everywhere.
- Use `pathlib` and CLI arguments, and never hard-code absolute paths. Defaults derive from `common.LAB3_DIR`.
- Use `logging`, not `print`. **No `matplotlib.pyplot` import anywhere** (§4.12).
- Unit tests never read the 77 MB CSV. Only `@pytest.mark.e2e` tests do.

---

## 9. Gotchas

- CRLF line endings, stray spaces in the header, and the duplicate header `Fwd Header Length` (§3).
- **Never install the default torch wheel.** It pulls several GB of `nvidia-*` CUDA packages. Always pass `--torch-backend=cpu` (a uv option). Plain `pip` users need `--extra-index-url https://download.pytorch.org/whl/cpu`; `requirements.txt` says so in a comment. `uv pip list | grep -i -E 'nvidia|cuda|triton'` may show only `nvidia-nccl-cu13` (about 200 MB). The xgboost Linux wheel depends on it, and it is harmless on CPU. Any other match means a CUDA torch build was installed.
- pandas `to_markdown` needs `tabulate` and `to_latex` needs `jinja2`; both are in `requirements.txt`.
- **XGBoost** prints one line per round unless `fit(..., verbose=False)` is passed (§4.9).
- **LSTM** needs `batch_first=True` (§4.9). Final run (2026-11-13, CPU, per-model epochs): the whole `main.py` takes 5.1 min (308 s). DL training: MLP 39 s (30 epochs), LSTM 53 s (15), CNN 68 s (early-stopped at 25). Earlier runs took 14 and 39 min only because other jobs were loading the CPU at the same time.
- **KNN** `predict_proba` with k=5 takes only the values {0, 0.2, …, 1}, so its ROC curve has few points. This is expected; say so in the report. KNN prediction (66k rows against 156k training rows, brute force) is the slowest classical step.
- **Near-perfect scores are expected.** The `errors_bar` figure, the FP/FN columns and the zoomed and log-x ROC figures exist for that reason.
- **GNB** is the weakest model, but not by much. In the P3 preview it reached F1 0.9909 on test: 327 FP against 0–44 for the others. Its errors are mostly false alarms. Report it as it is.
- **Cross-platform (Windows GPU vs Linux CPU, 2026-11-15).**
  - Epoch 1 of every DL model is identical on both (same seed, init and shuffle order); the runs drift from epoch 2 because CUDA/cuDNN kernels round differently. So DL numbers match only to about 3 decimals.
  - The **LSTM training is unstable on both platforms**: the train loss spikes (CPU epoch 3: 0.13→0.28; GPU epoch 5: 0.05→0.30). With patience 3 the GPU run stopped at epoch 7. Likely cause: exploding gradients over the 59-step sequence on heavy-tailed standardised inputs, with no gradient clipping. **User decision 2026-11-15: LSTM uses gradient clipping** (`GRAD_CLIP_NORM = 1.0` in `dl/lstm_dl.py`, `run_dl(..., grad_clip_norm=...)`; MLP/CNN do not clip, verified bit-identical MLP rerun). Linux CPU result (`outputs_lstm_clip_linux_cpu/`): F1 0.9943→0.9964, acc 0.9935→0.9958, recall 0.9939→0.9988, FN 118→23, ROC-AUC 0.9998 equal, but precision 0.9947→0.9940 and FP 101→116. The train-loss spikes are smaller, but the val loss still oscillates (0.016–0.086), so clipping reduces the instability without removing it. `outputs/` (full Windows run) still holds the unclipped LSTM.
  - LR differs by 3 FP: lbfgs stops at its tolerance, and different BLAS builds/thread counts reach it at a slightly different point. ML models are therefore "identical up to solver tolerance", not bit-identical.
  - **Times are not comparable across machines.** The Linux LR fit of 110 s was contention: re-measured on 2026-11-15 it takes 12.3 s (80 lbfgs iterations, OpenBLAS, 6 threads). The GPU gives no speed-up for the small MLP (≈1.7 s/epoch plus ≈7 s CUDA start-up) but a ≈1.8× per-epoch speed-up for the LSTM.
  - Artefacts: Linux CPU = `outputs/run.log` + `outputs/run_report.txt`; Windows GPU = `outputs/run_windows.log` + `outputs/run_report_windows.txt` (the user renamed the log on Windows for that run; `LOG_FILE_NAME` is back to `run.log`). `outputs/metrics/*` and `outputs/figures/*` hold the Windows run. A single-model re-run must use its own `--out` (WINDOWS.md §10).
- **Log-x ROC:** FPR = 0 cannot be drawn on a log axis, so clip it at 1e-5 (one false positive on the test set is about 7e-5).
- LR may warn with `ConvergenceWarning` on the heavy-tailed standardized data. Log the warning; do not silence it.
- The deck is open in LibreOffice (`.~lock.Security_Insider_lab_3.pptx#`). Never touch the lock file or the deck.
- Haiku has a 10-minute limit on foreground commands, so the full `main.py` run goes to the background.

---

## 10. Report and presentation (deferred by the user, decision D3; `TASKS.md` P8)

Not started. The user will ask for it later. This section keeps the agreed structure.

- **Deliverable:** `G8.Report3.pdf` (format `GX.ReportY.pdf`), 10–15 pages, short and clear, with screenshots. "Document everything." It is written in LaTeX by Sonnet in `Lab3/report/`. Reuse the Lab 2 Friday report template and its build rule (`../Lab2/Friday_Dataset/report/`, `latexmkrc_2`).
- **Submission (deck slides 3 and 12; the user sends it):**
  - send to tf@sec.uni-passau.de and aeg@sec.uni-passau.de
  - reply in the **same email thread** as the earlier reports; do not start a new email
  - subject: `Lab-2026: matriculation ID-1, matriculation ID-2`
  - the deadline was 2026-11-11
- **Presentation:** 2026-11-25. 10 min plus 2 min discussion; each member presents their own task; standard slide design.
- **Figure selection (D4):** the user picks figures from `outputs/figures/INDEX.md` (TASKS.md T6.6). Opus records the picks here, and the report and the deck use the same picks.
- **Numbers rule:** every number comes from `outputs/metrics/*`, and every figure from `outputs/figures/`.
- Do not commit to git unless the user asks.
