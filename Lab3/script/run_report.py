"""Self-contained plain-text run report for ``main.py --log-txt`` (Tasks 1-3).

The file is built in order so it can be handed to an LLM for verification:
header, configuration, the live run log (appended by a logging handler between
``start_report`` and ``finish_report``), then the preprocess summary, per-model
details, the val/test tables, confusion matrices and the list of output files.
"""
from __future__ import annotations

import datetime
import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np

import common
import comparison

RULE = "=" * 78
LIBRARIES = ["numpy", "pandas", "scikit-learn", "xgboost", "torch", "matplotlib"]
HASH_CHUNK = 1 << 20
JSON_INDENT = 2


def _section(title: str) -> str:
    """Format a section header.

    Args:
        title: Section title.

    Returns:
        Header block with rules and a trailing blank line.
    """
    return f"\n{RULE}\n== {title}\n{RULE}\n"


def _version(package: str) -> str:
    """Return the installed version of a package without importing it.

    Args:
        package: Distribution name.

    Returns:
        Version string, or "not installed".
    """
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def _torch_lines(device: str | None) -> list[str]:
    """Describe the torch device; torch is only inspected if already imported.

    Args:
        device: Resolved device ("cpu"/"cuda") or None when no DL model runs.

    Returns:
        Report lines.
    """
    torch = sys.modules.get("torch")
    if device is None or torch is None:
        return ["torch device: n/a (no DL model selected, torch not loaded)"]
    lines = [f"torch device: {device}", f"torch threads: {torch.get_num_threads()}"]
    if device == "cuda":
        lines += [f"GPU: {torch.cuda.get_device_name(0)}",
                  f"CUDA version (torch build): {torch.version.cuda}"]
    return lines


def header_text(argv: list[str], device: str | None) -> str:
    """Build the run header.

    Args:
        argv: Full command line (``sys.argv``).
        device: Resolved torch device or None.

    Returns:
        Header section text.
    """
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    lines = [f"UTC timestamp: {now}", f"command: {' '.join(argv)}", f"cwd: {Path.cwd()}",
             f"Python: {sys.version.replace(os.linesep, ' ')}",
             f"platform: {platform.platform()} ({platform.machine()})",
             f"CPU threads (os.cpu_count): {os.cpu_count()}"]
    lines += [f"{lib}: {_version(lib)}" for lib in LIBRARIES]
    lines += _torch_lines(device)
    return _section("RUN HEADER") + "\n".join(lines) + "\n"


def _sha256(path: Path) -> str:
    """Hash a file in chunks.

    Args:
        path: File to hash.

    Returns:
        Hex digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _train_settings(models: list[str]) -> dict[str, dict[str, object]]:
    """Return the effective lr, patience and clipping of every selected DL model.

    Args:
        models: Selected model keys.

    Returns:
        {key: {"lr", "patience", "grad_clip_norm"}}; empty if no DL model is selected.
        Torch is imported only for the selected DL models.
    """
    result: dict[str, dict[str, object]] = {}
    for key, module_name in (("mlp", "dl.mlp_dl"), ("lstm", "dl.lstm_dl"), ("cnn", "dl.cnn_dl")):
        if key not in models:
            continue
        module = importlib.import_module(module_name)
        # Models without overrides fall back to the shared defaults in common.
        result[key] = {"lr": getattr(module, "LEARNING_RATE", common.DL_LR),
                       "patience": getattr(module, "PATIENCE", common.DL_PATIENCE),
                       "grad_clip_norm": getattr(module, "GRAD_CLIP_NORM", None)}
    return result


def config_text(csv: Path, models: list[str], limits: dict[str, int]) -> str:
    """Build the configuration section.

    Args:
        csv: Input CSV path.
        models: Selected model keys.
        limits: Effective maximum epochs per selected DL model.

    Returns:
        Configuration section text.
    """
    lines = [f"SEED: {common.SEED}",
             f"split fractions (train/val/test): {common.TRAIN_FRAC}/{common.VAL_FRAC}/"
             f"{common.TEST_FRAC}",
             f"DROP_DUPLICATES: {common.DROP_DUPLICATES}",
             f"IDENTICAL_ATOL: {common.IDENTICAL_ATOL}",
             f"DL batch size: {common.DL_BATCH_SIZE}",
             f"DL learning rate, shared default (MLP, CNN): {common.DL_LR}",
             f"DL max epochs per model (this run): {limits or 'n/a'}",
             f"DL patience, shared default (MLP, CNN): {common.DL_PATIENCE}",
             f"DL train settings per model: {_train_settings(models) or 'n/a'}",
             f"selected models: {' '.join(models)}", f"csv path: {csv}"]
    if csv.is_file():
        lines += [f"csv size (bytes): {csv.stat().st_size}", f"csv sha256: {_sha256(csv)}"]
    else:
        lines.append("csv: file not found")
    return _section("CONFIGURATION") + "\n".join(lines) + "\n"


def start_report(path: Path, header: str, config: str) -> None:
    """Create the report with header, configuration and the run-log section title.

    Args:
        path: Report file (overwritten); parent directories are created.
        header: Output of ``header_text``.
        config: Output of ``config_text``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + config + _section("RUN LOG (all log lines of this run)"),
                    encoding="utf-8")


def _history_table(history: dict[str, list[float]]) -> str:
    """Format the per-epoch losses and mark the best epoch.

    Args:
        history: {"train_loss": [...], "val_loss": [...]}.

    Returns:
        Table text.
    """
    best = int(np.argmin(history["val_loss"]))  # the epoch whose weights are restored
    rows = ["epoch  train_loss  val_loss"]
    rows += [f"{i + 1:5d}  {t:10.5f}  {v:8.5f}{'  <- best' if i == best else ''}"
             for i, (t, v) in enumerate(zip(history["train_loss"], history["val_loss"]))]
    return "\n".join(rows) + f"\nbest epoch: {best + 1} of {len(rows) - 1}"


def _model_text(res: common.ModelResult) -> str:
    """Describe one model: family, timings and (DL) the epoch table.

    Args:
        res: Model result.

    Returns:
        Text block.
    """
    text = (f"### {res.name} ({res.key}, {res.family})\n"
            f"train time: {res.train_time_s:.3f} s\npredict time (test): "
            f"{res.predict_time_s:.3f} s\n(hyper-parameters / architecture: see the run log)\n")
    if res.history:
        text += _history_table(res.history) + "\n"
    return text


def _confusions_text(metrics: dict) -> str:
    """Format [[TN, FP], [FN, TP]] per model for val and test.

    Args:
        metrics: Output of ``evaluate_all``.

    Returns:
        Text block.
    """
    lines = []
    for key, entry in metrics.items():
        for split in ("val", "test"):
            m = entry[split]
            lines.append(f"{key} {split}: [[TN, FP], [FN, TP]] = "
                         f"[[{m['tn']}, {m['fp']}], [{m['fn']}, {m['tp']}]]")
    return "\n".join(lines) + "\n"


def _files_text(out_dir: Path, skip: Path) -> str:
    """List every file under the output root with its size.

    Args:
        out_dir: Output root.
        skip: The report itself (its size is still changing).

    Returns:
        Text block, one file per line.
    """
    files = sorted(p for p in out_dir.rglob("*") if p.is_file() and p.resolve() != skip.resolve())
    return "\n".join(f"{p.relative_to(out_dir).as_posix()}  {p.stat().st_size} bytes"
                     for p in files) + "\n"


def finish_report(path: Path, out_dir: Path, summary: Any, results: list[common.ModelResult],
                  metrics: dict) -> None:
    """Append the post-run sections to the report.

    Args:
        path: Report file started by ``start_report``.
        out_dir: Output root (for the file list).
        summary: Preprocess summary dict.
        results: Model results in run order.
        metrics: Output of ``evaluate_all``.
    """
    parts = [_section("PREPROCESS SUMMARY"), json.dumps(summary, indent=JSON_INDENT) + "\n",
             _section("PER-MODEL DETAILS"), "\n".join(_model_text(r) for r in results)]
    for split in comparison.SPLITS[::-1]:  # val first, then test
        parts += [_section(f"COMPARISON TABLE ({split.upper()})"),
                  comparison.table_markdown(comparison.build_table(metrics, split)) + "\n"]
    parts += [_section("CONFUSION MATRICES"), _confusions_text(metrics),
              _section("FILES WRITTEN UNDER --out"), _files_text(out_dir, path)]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("".join(parts))
