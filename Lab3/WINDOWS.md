# Running Lab 3 on Windows (NVIDIA RTX 3050, 6 GB)

Everything below is copy-paste PowerShell unless marked `cmd.exe`. All commands run from the `Lab3` folder.

## 1. Prerequisites

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
4. **Git LFS (only if needed).** This repo has no `.gitattributes`, so the CSV is a normal 77 MB file. If `Friday-WorkingHours-Afternoon-DDos.csv` is only a tiny pointer file (a few lines of text), run `git lfs install; git lfs pull`.
5. Optional, for deep paths: enable long paths (admin PowerShell): `New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force`.

## 2. Get the code

```powershell
git clone <repo-url> SecInsiderLab-1
cd SecInsiderLab-1\Lab3
```
(or copy the `Lab3` folder, including the CSV, and `cd` into it).

## 3. Virtual environment and packages

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

`requirements.txt` pins `torch==2.15.0`. Locally the installed version shows as a local variant such as `2.15.0+cu128`; that is the same release with CUDA support.

Verify the GPU is visible:
```powershell
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
Expected: `2.15.0+cu128 True NVIDIA GeForce RTX 3050 ...`. If `python` opens the Microsoft Store, use `.venv\Scripts\python.exe` instead (see section 9).

## 4. Quality checks (optional)

```powershell
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

Full pipeline (all 8 models; DL on the GPU) with the shareable report:
```powershell
python script\main.py --device cuda --log-txt outputs\run_report.txt
```
ML models only (no torch is loaded):
```powershell
python script\main.py --models gnb lr knn rf xgb
```
One classifier alone: `python script\main.py --models gnb` (also `lr`, `knn`, `rf`, `xgb`).

DL models only, on the GPU:
```powershell
python script\main.py --models mlp lstm cnn --device cuda
```
One DL model alone: `python script\main.py --models lstm --device cuda` (also `mlp`, `cnn`).

CPU fallback: `--device cpu`. The default `--device auto` uses CUDA if available, else CPU.
Epoch limits: each DL model has its own maximum (`MAX_EPOCHS` in its module: MLP 30, CNN 30, LSTM 15; early stopping may stop sooner). `--epochs N` overrides the limit of all DL models, e.g. `--epochs 5`.

Keep CPU and GPU runs apart with separate output folders:
```powershell
python script\main.py --device cpu  --out outputs_cpu --log-txt outputs_cpu\run_report.txt
python script\main.py --device cuda --out outputs_gpu --log-txt outputs_gpu\run_report.txt
```
Quick smoke run on the small fixture (seconds, any machine):
```powershell
python script\main.py --csv tests\fixtures\sample_ddos.csv --epochs 1 --out outputs_smoke --log-txt outputs_smoke\run_report.txt
```
If `python` does not resolve to the venv, write `.venv\Scripts\python.exe script\main.py ...`.

## 7. Outputs

- `metrics\`: `preprocess_summary.json`, `metrics.json`, `comparison_val.*`, `comparison_test.*`.
- `figures\`: every figure as PNG and PDF; `figures\INDEX.md` lists what each one shows, to pick figures for the report and deck.
- `run.log`: the console log.
- The `--log-txt` file is a single self-contained report (header with versions and GPU, configuration with the CSV sha256, full log, preprocess summary, per-epoch DL losses, val and test tables, confusion matrices, list of files). **This is the file to share with an LLM to verify the results.**

## 8. Expected runtime and results

Reference run (Linux, CPU only, per-model epoch limits, 2026-11-13): the full run took 5.1 min (308 s). DL training times: MLP 39 s, LSTM 53 s, 1D-CNN 68 s (the CNN early-stopped at epoch 25). The DL models should be faster on the RTX 3050; the ML models run on the CPU either way.

Reference test results (F1 / FP / FN): XGB 1.0000 / 0 / 0, RF 0.9999 / 0 / 3, KNN 0.9998 / 1 / 5, MLP 0.9995 / 6 / 12, CNN 0.9991 / 13 / 20, LR 0.9983 / 44 / 23, LSTM 0.9943 / 101 / 118, GNB 0.9909 / 327 / 26. The ML models should match exactly on any OS. DL results on the GPU may differ slightly in the last decimals: CUDA kernels are not bit-identical to the CPU ones, even with cuDNN deterministic mode enabled by the code.

## 9. Troubleshooting

- **`torch.cuda.is_available()` is False:** the CPU build of torch is installed or the driver is too old. Run `nvidia-smi`, update the driver, then reinstall: `uv pip install -r requirements.txt --torch-backend=cu128 --reinstall-package torch`. `--device cuda` stops with an error in this case, `--device auto` silently falls back to CPU.
- **CUDA out of memory:** lower `DL_BATCH_SIZE` (default 1024) in `script\common.py`, or run `--device cpu`. Close other GPU programs.
- **PowerShell blocks `Activate.ps1`:** `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use cmd.exe with `.venv\Scripts\activate.bat`.
- **`python` opens the Microsoft Store:** disable the "App execution aliases" for python in Windows settings, or call `.venv\Scripts\python.exe` directly.
- **Path separators:** use backslashes in PowerShell and cmd.exe as written; forward slashes also work in Python arguments. Quote paths that contain spaces.
- **CSV looks tiny:** it is a Git LFS pointer; run `git lfs install; git lfs pull`.
