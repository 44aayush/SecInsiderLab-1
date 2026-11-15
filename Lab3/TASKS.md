# TASKS.md: Lab 3 (Tasks 1–3: ML/DL pipeline; Tasks 4–5: eBPF/XDP, planned)

Read `CLAUDE.md` first: routing (§1), specs and user decisions (§2), verified data facts (§3), design (§4), module contract and figure catalog (§5, §5.1), layout (§6), commands (§7), quality rules (§8).

Legend: **[O]** Opus 5.5 (main session) · **[F]** Fable 5.2 (doc review) · **[S]** Sonnet 5.5 (code, tests, docs, LaTeX) · **[H]** Haiku 5.5 (commands, browser, light tasks) · **[U]** the user (sudo, screenshots, decisions).

Only Opus ticks boxes, and only after checking the acceptance criteria (AC). Commands run from `Lab3/` with `.venv` active unless a task says otherwise.

**Quality gate (applies to every [S] code task):**
- pylint 10.00/10 on the touched files
- `radon cc -n C` prints nothing for them
- every function has a docstring and type hints
- no `matplotlib.pyplot` import
- the task's tests pass

Dates: the report was due 2026-11-11 (past); the presentation is on 2026-11-25. **Task work starts only when the user prompts.**

---

## User decisions (2026-11-13)

- **D1 Duplicate rows: removed.** `common.DROP_DUPLICATES = True` (CLAUDE.md §4.4).
- **D2 Tasks 4–5 (eBPF/XDP): after Tasks 1–3.** P7 starts once P6 is signed off. The user installs the toolchain personally (T7.0).
- **D3 Report and presentation: not yet.** P8 stays as a placeholder (CLAUDE.md §10); the user will ask for it later.
- **D4 Comparison extras: keep them all, and generate several chart and grid variants** (CLAUDE.md §5.1). The user picks figures from `outputs/figures/INDEX.md` (T6.6), and the report and the deck reuse the picks.
- **D6 Windows/GPU, report, TP/TN, epochs:** `WINDOWS.md`, `--device`, `--log-txt`, TP/TN columns, and per-model DL epoch limits (MLP 30, CNN 30, LSTM 15), adopted only where no test metric got worse (CLAUDE.md §2).
- **D5 Layout: all Python code goes under `script/`.** The classifiers are in `script/clf/` and the DL models in `script/dl/`. Run with `python script/main.py` (CLAUDE.md §4.1, §6).

---

## P0: Planning

- [x] **T0.1 [O] Analyse the specs.**
  - `Task1.png`–`Task4.png` were read.
  - The deck text was extracted [H]: slides 3–12, including the deck-only Task 5, the deadlines and the submission rules.
  - The CSV sha256 equals Lab 2's copy.

  *AC:* CLAUDE.md §2 and §3 are filled in.
- [x] **T0.2 [O] Write `CLAUDE.md` and `TASKS.md`.**

  *AC:* every user instruction and decision of 2026-11-13 appears in CLAUDE.md §2 and maps to at least one task here.
- [x] **T0.3 [F → O] Review.** Fable reviewed both files (verdict: READY WITH FIXES, no blockers; 4 major, 13 minor, 5 nits). Opus applied all of them, after the user's "apply" (see "Review log").

  *AC:* no blocker or major findings are left open.

---

## P1: Environment

- [x] **T1.1 [H] Create the venv and install.** Ran `uv venv --python 3.12 .venv`, then installed the package set with `--torch-backend=cpu`, then `uv pip freeze`. Result, 2026-11-13:
  - Python 3.12.15
  - torch `2.15.0+cpu`, `cuda.is_available()` False, 6 threads
  - xgboost 3.4.1, pylint 4.1.3, pytest 9.2.0, radon 6.0.1
  - the only nvidia package is `nvidia-nccl-cu13` (an xgboost dependency)
  - `.venv` is 1.5 GB

  *AC:* met.
- [x] **T1.2 [S] Project config files.**
  - `requirements.txt`:
    - pin the direct dependencies with `==` from the T1.1 freeze: numpy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1, matplotlib 3.11.2, xgboost 3.4.1, torch 2.15.0, tabulate 0.10.0, jinja2 3.1.6, pylint 4.1.3, pytest 9.2.0, radon 6.0.1
    - group them with comments
    - add a header comment with the uv install command (`--torch-backend=cpu`) and the plain-pip alternative (`--extra-index-url https://download.pytorch.org/whl/cpu`)
  - `.python-version`: `3.12`.
  - `.pylintrc`:
    - `load-plugins=pylint.extensions.mccabe`, `max-complexity=10`
    - `source-roots=script` and `recursive=yes`, so that `pylint script tests` resolves `import common` and `from clf import ...`
    - `max-attributes=8`, with the reason comment "ModelResult contract, CLAUDE.md §5"
    - `generated-members` for torch
    - `good-names` adds `x,y,df,ax,fig`
    - every disable has a reason comment
  - `pytest.ini`: `pythonpath = script`, `testpaths = tests`, and the `e2e` marker registered.
  - `.gitignore`: `.venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.~lock.*#`. `outputs/` is **not** ignored (CLAUDE.md §4.2).

  *AC* (checked locally; the fresh install is T6.1):
  - all five files exist
  - `.venv/bin/pytest --collect-only -q` exits 0 or 5 (no tests yet), with no config or unknown-marker warnings
  - checked together with T2.1, once a module exists: `.venv/bin/pylint --rcfile=.pylintrc --disable=all --enable=E0015 script/common.py` reports no "unrecognized option" errors

---

## P2: Foundation

- [x] **T2.1 [S] `script/common.py`,** exactly as CLAUDE.md §5: constants including `FIG_DPI` and `MODEL_COLORS`, `DataSplits`, `ModelResult`, an idempotent `setup_logging`, and `save_figure`. It never imports torch or pyplot.
- [x] **T2.2 [S] `script/preprocess.py`,** following CLAUDE.md §4.4–4.7. Port the cleaning logic from `../Lab2/Friday_Dataset/src/ddosids/data.py` (copy and adapt; never import).
  - Small functions: `load_raw`, the step helpers (`drop_inf_nan_rows`, `drop_duplicate_rows`, `drop_constant_columns`, `drop_identical_columns`), `clean(df)` (steps 2–6; reads `common.DROP_DUPLICATES` at call time), `encode_labels`, `split_data`, `scale_splits`, and `preprocess`, which runs them in order.
  - Each step logs its counts. `preprocess` returns the summary dict with **exactly** the keys of CLAUDE.md §5.
- [x] **T2.3 [S] `script/evaluate.py`:** `compute_metrics` and `evaluate_all`, with exactly the §5 metric schema (`zero_division=0`; `y_pred = score > 0.5`).
- [x] **T2.4 [S] `script/clf/ml_common.py`** (plus `script/clf/__init__.py`): `run_sklearn`, following §5.
- [x] **T2.5 [S] Tests for P2.**
  - `tests/fixtures/sample_ddos.csv`: copy `../Lab2/Friday_Dataset/tests/fixtures/sample_ddos.csv` (3,187 rows: 1,665 BENIGN / 1,522 DDoS; 34 inf rows; CRLF). Record its sha256 in the `conftest.py` docstring.
  - `tests/conftest.py`: a fixture with a small synthetic `DataSplits` (`sklearn.datasets.make_classification`, 600 rows, 10 features, `random_state=42`, split 420/90/90, float32/int64), and the fixture CSV path.
  - `tests/test_preprocess.py` calls `clean(df)` on a hand-built DataFrame:
    - +inf, −inf and NaN rows are dropped and counted per class
    - duplicates are dropped; with `monkeypatch.setattr(common, "DROP_DUPLICATES", False)` they are kept, and `duplicate_rows.n == 0`
    - constant columns are dropped
    - an exact-copy column is dropped
    - a near-copy (diff 1e-9) is dropped, and a column that differs by 1e-3 is kept
    - the first occurrence is the one kept, and `identical_columns` maps dropped → kept
  - Other `preprocess` tests:
    - an unknown label raises `ValueError`
    - split sizes are 70/15/15 (±1 row) and stratified (class ratio within 1 percentage point in every split)
    - the split indices are disjoint
    - the scaler is fitted on train only (train column means ≈ 0; the val/test means are not forced to 0)
    - `preprocess(fixture CSV)` gives no inf/NaN, `y` ⊆ {0, 1}, float32 x arrays, a summary with exactly the §5 keys, and `json.dumps(summary)` succeeds
  - `tests/test_evaluate.py`:
    - hand-checked metrics and confusion matrix on a 10-sample example
    - `score == 0.5` → BENIGN
    - `json.dumps` of the `evaluate_all` output succeeds

  *AC:* the quality gate passes, and the P2 tests run in under 30 s.

---

## P3: Task 1, classifiers

- [x] **T3.1 [S] The five classifier files, in `script/clf/`:** `gnb_clf.py`, `lr_clf.py`, `knn_clf.py`, `rf_clf.py`, `xgb_clf.py`. Each has `KEY`, `NAME`, `build_model()` and `run(splits)`, with the hyper-parameters of CLAUDE.md §4.9. `run` delegates to `ml_common.run_sklearn`. XGB passes `fit_kwargs={"eval_set": [(x_val, y_val)], "verbose": False}`.
- [x] **T3.2 [S] `tests/test_classifiers.py`,** parametrised over the 5 modules on the synthetic `DataSplits`:
  - `KEY`/`NAME` match the §5 table
  - `family == "ML"`
  - score shapes equal the split sizes, and all scores are in [0, 1]
  - times are > 0
  - test accuracy is ≥ 0.8 (Fable measured 0.856–0.889)
  - `xgb_clf.run` prints nothing to stdout (`capsys`)

  *AC:* the quality gate passes.

---

## P4: Task 2, deep learning

- [x] **T4.1 [S] `script/dl/dl_common.py`** (plus `script/dl/__init__.py`): `set_seed`, `make_loader` (seeded generator), `EarlyStopper` (`update` returns True to stop and deep-copies the best `state_dict`; `restore`), `train_model` (uses `EarlyStopper` with `DL_PATIENCE`; history of `train_loss` and `val_loss` per epoch; restores the best weights), `predict_scores`, and `run_dl` (does not re-seed). Loss and optimiser are created here, following §4.9.
- [x] **T4.2 [S] The three DL files, in `script/dl/`:** `mlp_dl.py`, `lstm_dl.py`, `cnn_dl.py`, with the architectures of §4.9. Each has `KEY`, `NAME`, one `nn.Module` subclass `__init__(self, n_features)` that reshapes its input in `forward()` (the LSTM uses `batch_first=True` and `h_n[-1]`), and `run(splits, max_epochs)`, which calls `set_seed(SEED)` before it builds the model.
- [x] **T4.3 [S] `tests/test_dl.py`:**
  - for n_features in {10, 59}, each model maps a `(batch, n_features)` input to `(batch, 1)` logits
  - `run(..., max_epochs=2)` on the synthetic set gives a valid `ModelResult` (family `"DL"`, scores in [0, 1], `len(history["val_loss"]) <= 2`)
  - `EarlyStopper(patience=3)` fed the losses `[1.0, 0.8, 0.9, 0.85, 0.95]` returns `[False, False, False, False, True]`, and `restore` brings back the weights saved at the 0.8 epoch (use a tiny module with a distinct parameter value per epoch)
  - two `run` calls with the same seed give identical scores

  *AC:* the quality gate passes, and `test_dl.py` runs in under 60 s.

---

## P5: Task 3, comparison and `main.py`

- [x] **T5.1 [S] `script/comparison.py`:**
  - `FIGURE_CATALOG`, covering every §5.1 stem (with `confusion_<key>` as a pattern)
  - `build_table` with the §5 columns and sort order
  - `save_table`, writing `comparison_test.{csv,md,tex}` and `comparison_val.{csv,md,tex}` under `metrics/`
  - `plot_table_image`
  - `run_comparison`, which writes the tables and calls `plots_metrics.plot_all`, `plots_confusion.plot_all` and `plots_training.plot_all`
  - `write_figure_index`, which writes `figures/INDEX.md` with one entry per existing stem: chart type, purpose, and a relative link to the PNG
- [x] **T5.2 [S] `script/plots_metrics.py`:** the 7 metric charts of §5.1 (`metrics_bar_grouped`, `metrics_small_multiples`, `metrics_heatmap`, `metrics_radar`, `metrics_dot`, `errors_bar`, `time_bar`), one small function each, plus `plot_all`. They use `MODEL_COLORS` and work for 1–8 models.
- [x] **T5.3 [S] `script/plots_confusion.py` and `script/plots_training.py`:**
  - `confusion_grid_counts`, `confusion_grid_normalized` and `confusion_<key>`
  - `dl_history_overlay` and `dl_history_grid`, with the best epoch = argmin of val loss marked; skipped with a log line when there is no DL result
- [x] **T5.4 [S] `script/roc_curves.py`:** `plot_roc(results, y_test, out_dir)` writes `roc_test`, `roc_test_zoom`, `roc_test_logx`, `roc_grid`, `roc_test_ml` and `roc_test_dl`. Include the AUC in the legends and the chance diagonal. ML lines are solid and DL lines dashed. An empty family figure is skipped with a log line.
- [x] **T5.5 [S] `script/main.py`** runs in this order:
  1. parse the arguments (an unknown `--models` key gives an argparse error)
  2. `setup_logging(out)`
  3. `preprocess`, then write `metrics/preprocess_summary.json`
  4. run the selected models in registry order (ML, then DL) with lazy `importlib` imports of `clf.<key>_clf` / `dl.<key>_dl`, logging each model's train and predict time
  5. `evaluate_all`, then write `metrics/metrics.json` and log each model's test F1
  6. `comparison.run_comparison(results, metrics, out)`
  7. `roc_curves.plot_roc(results, splits.y_test, out)`
  8. `comparison.write_figure_index(out)`
  9. log the final test table, then return 0
- [x] **T5.6 [S] Tests.**
  - `tests/test_comparison.py`: tables built from fake metrics have the right columns and sort order; the csv/md/tex files are written; `write_figure_index` lists only the stems that exist.
  - `tests/test_plots.py`: for fake results and metrics of 3 models (2 ML + 1 DL), each `plot_all` and `plot_roc` writes its stems as png and pdf to `tmp_path`. With 2 ML models only, the DL figures and `roc_test_dl` are skipped without error.
  - `tests/test_main.py`:
    - smoke run: `main(["--csv", <fixture>, "--models", "gnb", "lr", "mlp", "--epochs", "1", "--out", <tmp_path>])` returns 0; every §6 file and every applicable §5.1 stem exists; `INDEX.md` lists exactly those stems
    - calling `main` twice does not duplicate the log lines
    - a subprocess check, run as `python script/main.py`: `--models gnb` leaves `"torch"` out of `sys.modules`

  *AC:* the quality gate passes, and the full non-e2e suite runs in under 120 s.
- [x] **T5.7 [S] `tests/test_e2e.py`** (`@pytest.mark.e2e`): `preprocess` on the full CSV gives a summary equal to the expected values in CLAUDE.md §5:
  - `raw_shape`, `raw_class_counts`, `inf_counts`, `nan_counts`, `inf_nan_rows` and `duplicate_rows`
  - the exact 10 constant and 9 identical column names: Lab 2's lists from `../Lab2/Friday_Dataset/tests/test_task3.py:174-180`, plus `Fwd Header Length.1` → `Fwd Header Length`
  - `clean_shape`, `clean_class_counts`, `split_sizes` and `split_class_counts`

  If a number differs, report it to Opus; do not edit the expectation.

  *AC:* the test exists and is deselected by `-m "not e2e"`. Its pass is checked in T6.3.

---

## P6: Verification and audit

- [x] **T6.1 [H] Fresh-env check.** **Do not activate `Lab3/.venv`.** `$SCRATCH` is the session scratchpad path given in the Haiku prompt.
  ```bash
  uv venv --python 3.12 "$SCRATCH/venv_check"
  uv pip install --python "$SCRATCH/venv_check/bin/python" -r requirements.txt --torch-backend=cpu
  uv pip check --python "$SCRATCH/venv_check/bin/python"
  "$SCRATCH/venv_check/bin/python" -c "import numpy, pandas, sklearn, matplotlib, xgboost, torch, tabulate, jinja2; print(torch.__version__)"
  rm -rf "$SCRATCH/venv_check"
  ```

  *AC:* the install succeeds, `uv pip check` is clean, and torch prints `2.15.0+cpu`.
- [x] **T6.2 [H] Lint and complexity.** Run `pylint script tests`, `radon cc -s -a script tests` and `radon cc -n C script tests`, and paste the output verbatim.

  *AC:* pylint is 10.00/10, and `radon -n C` prints nothing.
- [x] **T6.3 [H] Tests.** Run `pytest -m "not e2e" -q` and `pytest -m e2e -q`, and paste the output verbatim.

  *AC:* all tests pass.
- [x] **T6.4 [H] Full run.** Run `time python script/main.py` in the **background**. Paste verbatim: the wall time, `outputs/run.log`, `outputs/metrics/comparison_test.md`, `outputs/figures/INDEX.md` and `ls -R outputs/`.

  *AC:* exit code 0, every §6 file exists, and all 26 §5.1 stems exist as png and pdf.
- [x] **T6.5 [O] Audit.**
  - **Code:** follows the §5 contract and the §8 rules.
  - **No leakage:** the scaler and the column drops use no labels; the scaler sees train only; early stopping uses val only; the test set is touched once.
  - **Outputs:**
    - `comparison_test.md` equals `metrics.json` and the log
    - `preprocess_summary.json` equals §3/§5
    - the AUCs are plausible; the val/test gap is small (allowing for the bias of the early-stopped models)
    - the GNB, KNN and Destination Port caveats are noted
    - Opus looks at every figure for readability

  Fixes go to [S]; re-runs go to [H].

  *AC:* Opus signs off, and the findings and fixes are listed under "Review log".
- [ ] **T6.6 [U → O] Figure selection (D4).** The user browses `outputs/figures/INDEX.md` and picks the figures for the report and the deck. Opus records the picks in CLAUDE.md §10.

  *AC:* the picks are recorded.

---

## P7: Tasks 4–5, eBPF/XDP (starts after P6 sign-off; D2)

Toolchain on 2026-11-13 (T1.1 step D):
- kernel 7.0.0-42
- present: `/sys/kernel/btf/vmlinux`, bpftool 7.7.0, `ip`, `make`
- **missing:** clang, llc, libbpf headers (`bpf/bpf_helpers.h`), libxdp, xdp-tools
- interfaces: `lo`, `enp0s3` (UP), `docker0` (DOWN)

- [x] **T7.0 [U] Install the toolchain** (the user runs these personally):
  ```bash
  sudo apt update
  # Task 4: compile a small XDP program (clang/LLVM BPF backend, libbpf headers; gcc-multilib provides asm/types.h)
  sudo apt install -y clang llvm libbpf-dev gcc-multilib build-essential pkg-config
  # Task 5: build dependencies for xdp-tools from GitHub (it bundles its own libbpf/libxdp)
  sudo apt install -y git libelf-dev zlib1g-dev libpcap-dev m4
  ```
  Do **not** apt-install `xdp-tools` or `libxdp-dev`: Task 5 builds xdp-tools from GitHub, and a second copy on PATH would conflict. bpftool 7.7.0 and kernel BTF are already present.

  *AC:* [H] re-runs the check, and `clang --version`, `llc --version | grep -i bpf` and `ls /usr/include/bpf/bpf_helpers.h` all succeed.
- [x] **T7.1 [S] Theory notes, `xdp/THEORY.md`:**
  - what eBPF and XDP are: hook points, the verifier, maps, the XDP actions PASS/DROP/TX/REDIRECT/ABORTED, and the generic/native/offload modes
  - use cases: DDoS filtering, load balancing, monitoring
  - a short discussion of the available tools: xdp-tools (xdp-loader, xdp-filter, xdpdump), libbpf/libxdp, bcc, bpftrace, Cilium, Katran
  - sources cited
- [x] **T7.2 [S] Small XDP filter: `xdp/xdp_filter.c` and `xdp/Makefile`.**
  - The program parses Ethernet/IPv4/TCP-UDP, drops packets whose source IPv4 is in a BPF hash-map blocklist, and counts PASS/DROP in a per-CPU array map.
  - Build it with `clang -O2 -g -target bpf`.
  - Include a README section on attaching it in generic mode on `lo`.
- [x] **T7.3 [U + H] Demo.**
  1. Attach to `lo` (sudo).
  2. Add a blocklist entry with `bpftool map update`.
  3. Generate traffic (`ping`, `nc`).
  4. Show the counters with `bpftool map dump`.
  5. Detach.

  The user takes screenshots for the report.
- [x] **T7.4 [H + U] Task 5: xdp-tools from GitHub.** Clone it **outside** the course repo, to avoid a nested git repo:
  ```bash
  git clone --recurse-submodules https://github.com/xdp-project/xdp-tools.git ~/src/xdp-tools
  ```
  Then, in `~/src/xdp-tools`, [H] runs `./configure` and `make` and tees the output to `Lab3/xdp/logs/xdp-tools-build.log`. [U] runs the built binaries by path, for example `sudo ~/src/xdp-tools/xdp-loader/xdp-loader status` and an `xdp-filter` example; `sudo make install` is optional. This may slip to the Lab 4 deadline (slide 11).

  *AC:* `./configure` and `make` both exit 0, the build log is saved, and the user has a screenshot of `xdp-loader status`.

---

## P8: Report and presentation (deferred by the user; D3)

- [ ] **T8.1 [S] LaTeX report** in `report/`, giving `G8.Report3.pdf` (10–15 pages). Every number comes from `outputs/metrics/`, the figures are the T6.6 picks, and the screenshots come from the user (`SS/`).
- [ ] **T8.2 [U] Submit the report.** Email it to tf@sec.uni-passau.de and aeg@sec.uni-passau.de, replying in the **same thread** as the earlier reports, with the subject `Lab-2026: matriculation ID-1, matriculation ID-2`.
- [ ] **T8.3 [S] Presentation:** 10 min plus 2 min discussion; each member presents their own task; the same figure picks as the report.

---

## Review log

| Date | Source | Finding | Outcome |
|---|---|---|---|
| 2026-11-13 | Fable T0.3, F1 (major) | T6.1 would reuse the existing `.venv`, so the check passed vacuously | Applied: explicit throw-away venv with `--python` (T6.1) |
| 2026-11-13 | Fable F2 (major) | The summary and metrics dict schemas were prose only | Applied: literal key schemas with expected values (CLAUDE.md §5) |
| 2026-11-13 | Fable F3 (major) | The early-stopping and seed tests could not be written against the contract | Applied: `EarlyStopper`; seed before building the model (§4.9, §5, T4.3) |
| 2026-11-13 | Fable F4 (major) | The `DROP_DUPLICATES` test had no DataFrame-level function | Applied: `clean(df)` reads the flag at call time (§4.4, §5, T2.2) |
| 2026-11-13 | Fable F5 | The 8-field `ModelResult` exceeded pylint's `max-attributes` of 7 | Applied: `max-attributes=8`, documented (§8, T1.2) |
| 2026-11-13 | Fable F6 | The cleaning-order claim was inaccurate, and the `features.py` pointer was wrong | Applied: deviation note; `features.py` removed; dedup on the full row (§4.4) |
| 2026-11-13 | Fable F7 | XGBoost `verbose` defaults to True | Applied: `verbose=False` (§4.9, T3.1, T3.2) |
| 2026-11-13 | Fable F8 | `batch_first` was missing, and there was no `n_features` argument | Applied (§4.9, §5, T4.2, T4.3) |
| 2026-11-13 | Fable F9 | `out_dir`/`results` were ambiguous; val formats missing; no DL-less behaviour | Applied (§5 "Directory arguments", §6, T5.3) |
| 2026-11-13 | Fable F10 | No matplotlib backend was specified | Applied: OO `Figure` API, no pyplot (§4.12, §8) |
| 2026-11-13 | Fable F11 | No expectations for D1 = OFF | Moot: the user chose D1 = remove. The OFF path is covered by a unit test (T2.5) |
| 2026-11-13 | Fable F12 | Extras beyond `Task3.png` were not approved | Applied per D4: keep all; the §5.1 catalog with variants; `INDEX.md`; Macro-F1 column |
| 2026-11-13 | Fable F13 | Slide 3 submission rules were missing | Applied (§10, T8.2) |
| 2026-11-13 | Fable F14 | apt xdp-tools conflicted with the GitHub build; no submodules | Applied: apt removed (D2 edit), `--recurse-submodules`, configure/make AC (T7.4) |
| 2026-11-13 | Fable F15 | `setup_logging` was not idempotent | Applied (§4.13, §5, T5.6) |
| 2026-11-13 | Fable F16–F17 | The complexity wording; Sonnet running tests not marked as an interpretation | Applied (§8, §1 rule 3) |
| 2026-11-13 | Fable F18 | F1 was logged before `evaluate_all` | Applied (T5.5 steps 4–5) |
| 2026-11-13 | Fable F19–F20 | The val-score bias; the location of loss/optimiser | Applied (§4.8, §4.9) |
| 2026-11-13 | Fable F21 | Outdated "not run yet"; inconsistent size; pessimistic runtime | Applied: verified split class counts; 77 MB; estimate < 15 min (§3, §7, §9) |
| 2026-11-13 | Fable F22 | T1.2's AC was only checkable in P6; `outputs/` tracking was undecided | Applied: local AC; `outputs/` tracked (T1.2, §4.2) |
| 2026-11-13 | User D5 | Layout change | Applied: all code under `script/`, with `script/clf/` and `script/dl/` as packages; `pythonpath`/`source-roots` set to `script`; commands updated (CLAUDE.md §4.1, §5, §6, §7; T1.2, T2–T6) |
| 2026-11-13 | Opus P2 review | T1.2 + T2.1–T2.5 checked: 18 tests pass in 0.5 s; pylint 10.00/10; radon max B (7); the full-CSV summary equals §3/§5 exactly (Haiku re-run); the fixture sha256 equals Lab 2's. `script/preprocess.py` is 256 lines, over the ~200 guideline (mostly docstrings; every function is A–B) | Accepted as is. Extra test file `tests/test_common_ml.py` accepted |
| 2026-11-13 | Opus P3/P4 review | T3.1–T3.2 and T4.1–T4.3 checked: 47 unit tests pass in 4.8 s; pylint 10.00/10; all clf/dl blocks rank A; contract followed (XGB `verbose=False`; seed before build; `batch_first=True`; `EarlyStopper` restores best weights). Real-data preview (test): GNB F1 0.9909 (327 FP / 26 FN), LR 0.9983, KNN 0.9998, RF 0.9999, XGB 1.0000 (0 errors); DL after 1 epoch: MLP 0.993, CNN 0.987, LSTM 0.942. Epoch time: MLP 2.4 s, CNN 4.2 s, LSTM 4.5 s | Accepted. `dl_common.py` is 229 lines (docstrings), accepted like `preprocess.py`. The §9 GNB note is corrected: it scores high here, so it is not "clearly lower" |
| 2026-11-13 | Opus P5 review | T5.1–T5.7 accepted. Extra `script/plot_utils.py` and the conftest fixtures accepted. The e2e twin mapping equals the independent P2 Haiku run. `plots_metrics.py` is 264 lines (accepted). Times use 3 decimals | Accepted |
| 2026-11-13 | Opus T6.5 audit (open) | T6.1–T6.4 pass: fresh env OK; pylint 10.00; radon avg A; 62 + 3 tests pass; full run exit 0 in 13:38, 26 png + 26 pdf. Test F1: XGB 1.0000, RF 0.9999, KNN 0.9998, MLP 0.9994, CNN 0.9986, LR 0.9983, LSTM 0.9943, GNB 0.9909. Val and test agree. **Findings:** (a) no DL model early-stopped: best epochs 15/14/15 of 15, so the DL models may be under-trained (user decision: raise `DL_MAX_EPOCHS`?); (b) the radar radial labels overlap the "Accuracy" label and the legend; (c) the normalised confusion grid shows %, but the user chose 0.9999 decimals; (d) LSTM 407 s and CNN 222 s for 15 epochs, much slower than the P4 estimate | (a) waits for the user; (b), (c) fixes to [S], then re-run [H] |
| 2026-11-13 | Opus D6 | 30-epoch experiment vs 15, on test. MLP: F1 .9994→.9995, FP 8→6, FN 16→12, all metrics ≥. CNN: F1 .9986→.9991, FP 21→13, FN 32→20, all ≥. LSTM: F1 .9943→.9960, FN 118→27, but precision .9947→.9935 and FP 101→126 got worse | MLP and CNN set to 30; LSTM kept at 15 |
| 2026-11-13 | Opus D6 review | `--log-txt` (`run_report.py`), TP/TN columns, `--device`, the radar and normalised-confusion fixes (T6.5 b, c), WINDOWS.md. 68 + 3 tests pass; pylint 10.00; radon OK. The CUDA path is untested here (no GPU). `dl_common.py` 283, `run_report.py` 238 and `plots_metrics.py` 270 lines (accepted). One WINDOWS.md wording fix (e2e timing) sent to [S] | Accepted; the final full re-run goes to [H] |
| 2026-11-13 | Opus T6.5 sign-off | Final re-run: pylint 10.00; radon OK; 68 + 3 tests pass; full run exit 0 in 308 s; 26 png + 26 pdf; `run_report.txt` 590 lines with all 9 sections. Results equal the experiment exactly (ML unchanged; MLP/CNN equal the 30-epoch run; LSTM equals the 15-epoch run), so the run is reproducible. Val and test agree. Leakage checks passed (P2 review). Findings (b) and (c) fixed | **T6.5 signed off.** Results are in CLAUDE.md §3. T6.6 (figure picks) waits for the user |
| 2026-11-13 | Opus | `history["best_epoch"]` was redundant | Removed: the best epoch is derived as argmin of val loss (§5) |
| 2026-11-15 | Opus Windows-run analysis | Windows 11, RTX 3050 Laptop, torch 2.15.0+cu132, `--device cuda`, same CSV sha256 and split. GNB/KNN/RF/XGB identical to CPU; LR FP 44→41 (solver tolerance); MLP F1 .9996 (FP 7, FN 9); CNN better on all metrics (FP 6, FN 19, early stop 26); **LSTM F1 .9885, FP 430**: loss spike at epoch 5, early stop at 7. Loss spikes also on CPU (epoch 3), so LSTM training is unstable on both. Linux LR 110 s re-measured at 12.3 s (contention). Details in CLAUDE.md §3 and §9 | Accepted as a valid run. LSTM gradient clipping proposed, needs user approval. `LOG_FILE_NAME` rename was a Windows-only edit; reverted to `run.log` on 2026-11-15 |
| 2026-11-15 | Opus T7.0 | [H] check: clang 21.1.8, llc has bpf targets, `bpf/bpf_helpers.h` and `asm/types.h` present, libbpf 1.6.3, bpftool 7.7.0, kernel BTF present | **T7.0 done** |
| 2026-11-15 | Opus T7.1/T7.2 review | `xdp/THEORY.md` (106 lines, 7 sources), `xdp/xdp_filter.c` (136), `Makefile` (59), `README.md` (89), `.gitignore` (`*.o`). Builds with `-Wall -Werror`, no warnings (`xdp/logs/build.log`); sections `xdp`, `.maps`, `license`, `.BTF` present; maps blocklist (hash 1024, u32→u8) and stats (percpu array 2, u64). Bounds checks reviewed: eth, iph, ihl ≥ 5, options, TCP/UDP. Verifier load and attach not run (root) | **T7.1, T7.2 done.** T7.3 waits for the user |
| 2026-11-15 | Opus T7.4 (build part) | [H] cloned xdp-tools 92a9828 (2026-11-08, libbpf submodule v1.7.0) to `~/src/xdp-tools`; `./configure` exit 0 (system libbpf 1.6.3, cap-ng no), `make` exit 0; `xdp/logs/xdp-tools-build.log` (125 lines); xdp-loader, xdp-filter, xdpdump, xdp-bench built | Build AC met; the `xdp-loader status` screenshot waits for the user |
| 2026-11-15 | Opus T7.3/T7.4 screenshot review (`xdp/SS_T7/SS_T7_1..7.png`) | T7.3 passes: attached as xdpgeneric prog id 118 on lo (verifier accepted it, jited 892 B, maps 27/28); baseline ping from 127.0.0.2 0% loss; after `make block` ping from 127.0.0.1 0% loss and from 127.0.0.2 100% loss; stats PASS 14 (1+7+6), DROP 3 (cpu 4) = exactly the 3 echo requests; unblock and detach clean. T7.4: `xdp-loader status` OK, but `xdp-filter load` failed (`Couldn't find a BPF file with name xdpfilt_alw_all.o`): uninstalled build, libxdp looks in `/usr/local/lib/bpf`; the later `ip`/`status`/ping steps therefore show no filter | **T7.3 done.** T7.4: re-run with `LIBXDP_OBJECT_PATH` pointing to the build dir (screenshots SS_T7_8+) |
| 2026-11-15 | Opus LSTM clipping review | [S] `make_step` + `grad_clip_norm` (LSTM only, 1.0), report config line, 2 new tests (70 pass), pylint 10.00, radon OK. [H] Linux CPU LSTM → `outputs_lstm_clip_linux_cpu/` (68.7 s): test F1 0.9964, FP 116, FN 23 (was 0.9943 / 101 / 118). MLP rerun without clipping is identical to §3 (FP 6, FN 12), so MLP/CNN are unaffected | Accepted (user decision). Precision/FP slightly worse than unclipped CPU: reported to the user. Windows GPU clipped run waits for the user (WINDOWS.md §10) |
| 2026-11-15 | Opus T7.4 screenshot review (SS_T7_8, SS_T7_9) | With `LIBXDP_OBJECT_PATH` set, `xdp-filter load lo -m skb -f ipv4` succeeds; `xdp-loader status` shows `xdp_dispatcher` (skb, id 136) chaining `xdpfilt_alw_ip` (prio 10, id 145, chain action XDP_PASS). After `xdp-filter ip 127.0.0.2 -m src`, ping from 127.0.0.1 0% loss, from 127.0.0.2 100% loss | **T7.4 done** (AC met). Optional: `xdp-filter status` (counters) and unload screenshots |
| 2026-11-15 | Opus SS_T7_10/11 review | `xdp-filter status`: XDP_DROP 3, XDP_PASS 8, ABORTED 0; xdpfilt_alw_ip on lo (skb), features ipv6,ipv4,allow (the `alw_ip` object covers both IP versions); 127.0.0.2 mode src, hit counter 3 = the 3 blocked echo requests. Unload leaves all interfaces with no XDP program | P7 complete; screenshot set SS_T7_1..11 |
| 2026-11-15 | Opus D7 LSTM tuning | [S] `TrainSettings` (per-model lr/patience/clip), LSTM constants, run_report line, tests (73 pass), pylint 10.00, radon OK. [H] grid (selection by val loss): lr 5e-4/p5/cap30 0.00567 (hit cap), lr 3e-4/p5/cap40 0.00720, **lr 5e-4/p7/cap40 0.00529**. Official run → `outputs_lstm_enhance_linux_cpu/`: test F1 0.9992, prec 0.9992, rec 0.9992, FP 16, FN 16, best epoch 31, stop 38, 137 s; identical to the grid run (reproducible) | Accepted: better than every earlier LSTM on every metric. Windows enhanced run waits for the user (WINDOWS.md §10). Open: full 8-model re-run so `outputs/` carries the D7 LSTM |
