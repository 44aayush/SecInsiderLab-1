# Lab 3 — Training ML and DL models for DDoS detection

Security Insider Lab I, group G8.

- **Tasks 1–3:** train five classical classifiers (Gaussian NB, Logistic Regression, KNN, Random Forest, XGBoost) and three neural networks (MLP, LSTM, 1D-CNN, PyTorch) on the CIC-IDS2017 Friday DDoS flow file, then compare all eight models (metric tables, ROC curves, confusion matrices, training curves).
- **Task 4:** XDP programs in `xdp/`: a source-IP blocklist filter and a per-source rate limiter.
- **Task 5:** build and check `xdp-tools` (see `xdp/README.md`).

Task spec: [Security_Insider_lab_3.pptx](Security_Insider_lab_3.pptx) ([Task1.png](Task1.png), [Task2.png](Task2.png), [Task3.png](Task3.png), [Task4.png](Task4.png)).
Report: [report/G8.Report3.pdf](report/G8.Report3.pdf). Slides: [report/ppt/G8.Lab3.Presentation.pptx](report/ppt/G8.Lab3.Presentation.pptx).

## Layout

| Path | Content |
|---|---|
| `script/` | `main.py` (entry point), preprocessing, evaluation, comparison and plot modules |
| `script/clf/` | one file per classical classifier |
| `script/dl/` | one file per neural network (MLP, LSTM, CNN) |
| `tests/` | unit and end-to-end tests (`pytest.ini`) |
| `outputs/` | tracked results: `metrics/`, `figures/`, `run_report.txt`, `runs/` |
| `xdp/` | XDP filter, rate limiter (`xdp/ratelimit/`), xdp-tools notes |
| `report/` | LaTeX report and presentation |

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python 3.12 is managed by uv)
- `git lfs pull` so the CSV is the real file, not a pointer
- Only for the XDP programs: clang, llvm, libbpf-dev, gcc-multilib, bpftool, iproute2

## Run everything

```bash
bash run.sh            # full run
bash run.sh --quick    # smoke run
```

The script creates `.venv`, installs `requirements.txt` (CPU PyTorch), runs `script/main.py`, runs pytest, and builds the XDP programs if `clang` is present. It never uses sudo.

- A **full run** trains everything and **rewrites the tracked `outputs/`**.
- `--quick` trains with 1 epoch, writes to the git-ignored `outputs_quick/`, and skips the end-to-end tests (`-m "not e2e"`).

> [!NOTE]
> **For a GPU run, see [GPU.md](GPU.md).**

> [!IMPORTANT]
> **The XDP part requires `sudo`.** Steps are in [xdp/README.md](xdp/README.md) and [xdp/ratelimit/README.md](xdp/ratelimit/README.md).

## XDP demo (Tasks 4–5)

`xdp_filter.c` drops packets whose IPv4 source is in a BPF hash map;
`xdp/ratelimit/xdp_ratelimit.bpf.c` lets each source send 100 packets per second and drops the rest.

Both build without root (`make -C xdp`, `make -C xdp/ratelimit`). 

Attaching, editing the maps and reading the counters need sudo, so `run.sh` does not do them. 

Steps are in [xdp/README.md](xdp/README.md) and [xdp/ratelimit/README.md](xdp/ratelimit/README.md).
