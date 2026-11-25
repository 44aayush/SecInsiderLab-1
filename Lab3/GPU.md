# Running Lab 3 on a GPU (Windows, NVIDIA RTX 3050, 6 GB)

Every step with commands comes in two variants: **PowerShell** and **Git Bash**. Pick your shell in the table of contents. All commands run from the `Lab3` folder (`cmd.exe` is mentioned where it differs).

`bash run.sh` is Linux-only: it uses `.venv/bin/python` (on Windows the venv has `.venv/Scripts/python.exe`) and installs the CPU build of PyTorch. Git Bash users should run the commands listed below instead.

## Table of contents

1. [Prerequisites](#1-prerequisites): [PowerShell](#powershell-prerequisites) | [Git Bash](#git-bash-prerequisites)
2. [Get the code](#2-get-the-code): [PowerShell](#powershell-get-the-code) | [Git Bash](#git-bash-get-the-code)
3. [Virtual environment and packages](#3-virtual-environment-and-packages): [PowerShell](#powershell-virtual-environment-and-packages) | [Git Bash](#git-bash-virtual-environment-and-packages)
4. [Quality checks (optional)](#4-quality-checks-optional): [PowerShell](#powershell-quality-checks) | [Git Bash](#git-bash-quality-checks)
5. [Train, validate and test: one run does all three](#5-train-validate-and-test-one-run-does-all-three)
6. [Running](#6-running): [PowerShell](#powershell-running) | [Git Bash](#git-bash-running)
7. [Outputs](#7-outputs)
8. [Expected runtime and results](#8-expected-runtime-and-results)
9. [Troubleshooting](#9-troubleshooting)
10. [Re-running only the LSTM (enhanced settings)](#10-re-running-only-the-lstm-enhanced-settings): [PowerShell](#powershell-re-run-the-lstm) | [Git Bash](#git-bash-re-run-the-lstm)

## 1. Prerequisites

### PowerShell: prerequisites

1. **NVIDIA driver.** Check it works:
   ```powershell
   nvidia-smi
   ```
   It must list the RTX 3050 and a "CUDA Version". No CUDA toolkit install is needed; the PyTorch wheel ships its own CUDA runtime.
2. **Git** (https://git-scm.com/download/win).
3. **uv** (Python package manager), official installer:
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Close and reopen PowerShell afterwards so `uv` is on the PATH.
4. **Git LFS (required).** The CSV is stored with Git LFS. After cloning, run `git lfs install; git lfs pull`. If `Friday-WorkingHours-Afternoon-DDos.csv` is only a few lines of text, it is still an LFS pointer.
5. Optional, for deep paths: enable long paths (admin PowerShell): `New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force`.

### Git Bash: prerequisites

1. **NVIDIA driver.** Check it works:
   ```bash
   nvidia-smi
   ```
   It must list the RTX 3050 and a "CUDA Version". No CUDA toolkit install is needed; the PyTorch wheel ships its own CUDA runtime.
2. **Git** (https://git-scm.com/download/win). Git Bash comes with it.
3. **uv** (Python package manager), official installer (it calls PowerShell, so it works from Git Bash too):
   ```bash
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Close and reopen Git Bash afterwards so `uv` is on the PATH.
4. **Git LFS (required).** The CSV is stored with Git LFS. After cloning, run `git lfs install && git lfs pull`. If `Friday-WorkingHours-Afternoon-DDos.csv` is only a few lines of text, it is still an LFS pointer.
5. Optional, for deep paths: long paths can only be enabled from an admin PowerShell (see the PowerShell variant above).

## 2. Get the code

### PowerShell: get the code

```powershell
git clone <repo-url> SecInsiderLab-1
cd SecInsiderLab-1\Lab3
```
(or copy the `Lab3` folder, including the CSV, and `cd` into it).

### Git Bash: get the code

```bash
git clone <repo-url> SecInsiderLab-1
cd SecInsiderLab-1/Lab3
```
(or copy the `Lab3` folder, including the CSV, and `cd` into it).

## 3. Virtual environment and packages

### PowerShell: virtual environment and packages

```powershell
uv venv --python 3.12 .venv
.venv\Scripts\Activate.ps1
```
If PowerShell refuses to run the script, allow local scripts once, then retry:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
`cmd.exe` activation: `.venv\Scripts\activate.bat`.

Install (the key option is `--torch-backend=auto`: uv reads your NVIDIA driver and picks the matching CUDA build of PyTorch):
```powershell
uv pip install -r requirements.txt --torch-backend=auto
```
If `auto` picks a wrong build or CUDA is not detected later, force one: `--torch-backend=cu128` (or `cu126` for older drivers).

`requirements.txt` pins `torch==2.15.0`. Locally the installed version shows as a local variant such as `2.15.0+cu132` (or `+cu128`); the suffix depends on the driver, and it is the same release with CUDA support.

Verify the GPU is visible:
```powershell
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
Expected: `2.15.0+cu132 True NVIDIA GeForce RTX 3050 ...`. If `python` opens the Microsoft Store, use `.venv\Scripts\python.exe` instead (see section 9).

### Git Bash: virtual environment and packages

```bash
uv venv --python 3.12 .venv
source .venv/Scripts/activate
```
(or skip activation and call `.venv/Scripts/python` directly, for example `.venv/Scripts/python script/main.py ...`).

Install (same `--torch-backend=auto` as above):
```bash
uv pip install -r requirements.txt --torch-backend=auto
```
If `auto` picks a wrong build or CUDA is not detected later, force one: `--torch-backend=cu128` (or `cu126` for older drivers). The torch version notes above apply unchanged.

Verify the GPU is visible:
```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
Expected: `2.15.0+cu132 True NVIDIA GeForce RTX 3050 ...`. If `python` opens the Microsoft Store, use `.venv/Scripts/python` instead (see section 9).

## 4. Quality checks (optional)

### PowerShell: quality checks

```powershell
pylint script tests
radon cc -n C script tests
pytest -m "not e2e" -q
pytest -m e2e -q
```

### Git Bash: quality checks

```bash
pylint script tests
radon cc -n C script tests
pytest -m "not e2e" -q
pytest -m e2e -q
```

`pylint` must score 10.00/10, `radon` must print nothing. The e2e tests read the full 77 MB CSV (about 5–20 s).

## 5. Train, validate and test: one run does all three

Every run of `main.py` trains, validates and tests in a single go. There is no separate "validate" or "test" command.

- **Train:** each model is fitted on the 70 % train split.
- **Validate:** the 15 % validation split drives early stopping of the DL models and gives the validation metrics.
- **Test:** the 15 % test split is scored once, after training. The final comparison is on the test split.

Where each result lands (under `--out`, default `outputs\`):

| What | Location |
|---|---|
| Validation table | `metrics\comparison_val.csv/.md/.tex` |
| Test table (the one for the report) | `metrics\comparison_test.csv/.md/.tex` |
| All numbers, per model | `metrics\metrics.json`, keys `val` and `test` |
| Every log line | `run.log` |
| Everything in one shareable file | the `--log-txt` report |


## 6. Running

### PowerShell: running

Full pipeline (all 8 models; DL on the GPU) with the shareable report:
```powershell
python script\main.py --device cuda --log-txt outputs\run_report.txt
```
This writes everything into one consolidated folder, `outputs\` (log: `outputs\run.log`).
ML models only (no torch is loaded):
```powershell
python script\main.py --models gnb lr knn rf xgb
```
DL models only, on the GPU:
```powershell
python script\main.py --models mlp lstm cnn --device cuda
```
Quick smoke run on the small fixture (seconds, any machine):
```powershell
python script\main.py --csv tests\fixtures\sample_ddos.csv --epochs 1 --out outputs_smoke --log-txt outputs_smoke\run_report.txt
```
If `python` does not resolve to the venv, write `.venv\Scripts\python.exe script\main.py ...`.

### Git Bash: running

Full pipeline (all 8 models; DL on the GPU) with the shareable report:
```bash
python script/main.py --device cuda --log-txt outputs/run_report.txt
```
This writes everything into one consolidated folder, `outputs/` (log: `outputs/run.log`).
ML models only (no torch is loaded):
```bash
python script/main.py --models gnb lr knn rf xgb
```
DL models only, on the GPU:
```bash
python script/main.py --models mlp lstm cnn --device cuda
```
Quick smoke run on the small fixture (seconds, any machine):
```bash
python script/main.py --csv tests/fixtures/sample_ddos.csv --epochs 1 --out outputs_smoke --log-txt outputs_smoke/run_report.txt
```
If `python` does not resolve to the venv, write `.venv/Scripts/python script/main.py ...`.

### Options (both shells)

One classifier alone: `python script/main.py --models gnb` (also `lr`, `knn`, `rf`, `xgb`). One DL model alone: `python script/main.py --models lstm --device cuda` (also `mlp`, `cnn`). In PowerShell write the paths with backslashes (`script\main.py`).

CPU fallback: `--device cpu`. The default `--device auto` uses CUDA if available, else CPU.
Epoch limits: each DL model has its own maximum (`MAX_EPOCHS` in its module: MLP 40, CNN 30, LSTM 40; early stopping may stop sooner). The LSTM also has its own learning rate 5e-4, patience 7 and gradient clipping 1.0 (constants in `script\dl\lstm_dl.py`). `--epochs N` overrides the limit of all DL models, e.g. `--epochs 5`.

Single-model re-runs go to a separate `outputs_<name>` folder so they do not overwrite `outputs\` (see section 10). These folders are git-ignored and can be deleted afterwards.

## 7. Outputs

- `metrics\`: `preprocess_summary.json`, `metrics.json`, `comparison_val.*`, `comparison_test.*`.
- `figures\`: every figure as PNG and PDF; `figures\INDEX.md` lists what each one shows, to pick figures for the report and deck.
- `run.log`: the console log.
- The `--log-txt` file is a single self-contained report (header with versions and GPU, configuration with the CSV sha256, full log, preprocess summary, per-epoch DL losses, val and test tables, confusion matrices, list of files). **This is the file to share with an LLM to verify the results.**

## 8. Expected runtime and results

Reference run (Linux, CPU only, per-model epoch limits, consolidated run of 2026-11-15): the full run took 298 s. DL training times: MLP 39 s (about 39 to 42 s; early-stopped at epoch 32 with cap 40), LSTM 141 s (stopped at epoch 38), 1D-CNN 67 s (stopped at epoch 25). The DL models should be faster on the RTX 3050; the ML models run on the CPU either way.

Reference test results (F1 / FP / FN): XGB 1.0000 / 0 / 0, RF 0.9999 / 0 / 3, KNN 0.9998 / 1 / 5, MLP 0.9995 / 6 / 12, LSTM 0.9992 / 16 / 16, CNN 0.9991 / 13 / 20, LR 0.9983 / 44 / 23, GNB 0.9909 / 327 / 26. GNB, KNN, RF and XGBoost matched the Linux results exactly on the 2026-11-15 Windows run, while Logistic Regression differed by 3 FP (lbfgs stops at its tolerance, and different BLAS builds reach it at a slightly different point). DL results on the GPU may differ slightly in the last decimals: CUDA kernels are not bit-identical to the CPU ones, even with cuDNN deterministic mode enabled by the code.

## 9. Troubleshooting

- **`torch.cuda.is_available()` is False:** the CPU build of torch is installed or the driver is too old. Run `nvidia-smi`, update the driver, then reinstall: `uv pip install -r requirements.txt --torch-backend=cu128 --reinstall-package torch`. `--device cuda` stops with an error in this case, `--device auto` silently falls back to CPU.
- **CUDA out of memory:** lower `DL_BATCH_SIZE` (default 1024) in `script\common.py`, or run `--device cpu`. Close other GPU programs.
- **PowerShell blocks `Activate.ps1`:** `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use cmd.exe with `.venv\Scripts\activate.bat`.
- **`python` opens the Microsoft Store:** disable the "App execution aliases" for python in Windows settings, or call `.venv\Scripts\python.exe` directly.
- **Path separators:** use backslashes in PowerShell and cmd.exe as written; forward slashes also work in Python arguments. Quote paths that contain spaces.
- **CSV looks tiny:** it is a Git LFS pointer; run `git lfs install; git lfs pull`.


- **Git Bash: `source .venv/Scripts/activate` fails or `python` is not the venv one:** check that `.venv/Scripts/` exists (not `.venv/bin/`), or call `.venv/Scripts/python` directly.
- **CSV looks tiny:** it is a Git LFS pointer; run `git lfs install; git lfs pull`.

## 10. Re-running only the LSTM (enhanced settings)

The LSTM now uses enhanced settings (2026-11-15), chosen by lowest validation loss: learning rate 5e-4, patience 7, gradient-norm clipping 1.0 and a cap of 40 epochs (constants in `script\dl\lstm_dl.py`). MLP and CNN are unchanged.

1. Pull the new code: `git pull` (then `git lfs pull` if the CSV is a pointer).

Use a NEW output folder. `--out` defaults to `outputs\`, and a single-model run overwrites `metrics\metrics.json`, `metrics\comparison_*.*`, `figures\` and `run.log` there with a 1-model result. The `outputs_<name>` folder is git-ignored and can be deleted after the run; do not commit it.


### PowerShell: re-run the LSTM

```powershell
.venv\Scripts\Activate.ps1
python script\main.py --models lstm --device cuda --out outputs_lstm --log-txt outputs_lstm\run_report_lstm_enhance_windows_gpu.txt
```

### Git Bash: re-run the LSTM

```bash
source .venv/Scripts/activate
python script/main.py --models lstm --device cuda --out outputs_lstm --log-txt outputs_lstm/run_report_lstm_enhance_windows_gpu.txt
```

How to check: open `outputs_lstm\metrics\comparison_test.md`. The report file lists the per-epoch losses and the settings line (lr 0.0005, patience 7, grad clip 1); look for "early stop at epoch" and for jumps in the loss.

Run evidence is kept as text files in `outputs\runs\`:
- `run_report_windows_gpu_full_untuned_lstm.txt` and `run_windows_gpu_full_untuned_lstm.log`: full Windows GPU run, before the LSTM changes.
- `run_report_lstm_clip_linux_cpu.txt`: Linux CPU, clip-only LSTM.
- `run_report_lstm_enhance_linux_cpu.txt`: Linux CPU, enhanced LSTM.
- `run_report_lstm_enhance_windows_gpu.txt`: Windows GPU, enhanced LSTM.

Notes:
- The LSTM's maximum is 40 epochs (`MAX_EPOCHS` in `script\dl\lstm_dl.py`); `--epochs N` overrides it.
- Preprocessing reruns every time (a few seconds).
- Results reproduce on the same machine and device, but GPU and CPU differ (see section 8).
- Reference numbers, before clipping. Full Windows GPU run, 2026-11-15: LSTM test F1 0.9885, FP 430, FN 17, early stop at epoch 7 (best epoch 4). Linux CPU (old cap): F1 0.9943, FP 101, FN 118.
- Linux CPU clip-only (2026-11-15): F1 0.9964, FP 116, FN 23.
- Linux CPU enhanced (2026-11-15): accuracy 0.9990, precision 0.9992, recall 0.9992, F1 0.9992, ROC-AUC 1.0000, FP 16, FN 16; best epoch 31, early stop at 38; training 137 s on CPU.
