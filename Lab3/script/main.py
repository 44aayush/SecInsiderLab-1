"""Entry point for Tasks 1-3: preprocess, train 5 ML + 3 DL models, compare.

Usage: ``python script/main.py [--csv F] [--out DIR] [--models gnb lr ...] [--epochs N]
[--device auto|cpu|cuda] [--log-txt FILE]``.
Model modules are imported lazily so ``--models gnb`` never loads torch
(CLAUDE.md 4.14).
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
from pathlib import Path
from typing import Any

import common
import comparison
import evaluate
import preprocess
import roc_curves
import run_report

log = logging.getLogger(__name__)

ML_KEYS = ["gnb", "lr", "knn", "rf", "xgb"]
DL_KEYS = ["mlp", "lstm", "cnn"]
ALL_KEYS = ML_KEYS + DL_KEYS
JSON_INDENT = 2
DEVICE_CHOICES = ["auto", "cpu", "cuda"]


def _module_name(key: str) -> str:
    """Map a registry key to its import name.

    Args:
        key: Model key.

    Returns:
        "clf.<key>_clf" or "dl.<key>_dl".
    """
    return f"clf.{key}_clf" if key in ML_KEYS else f"dl.{key}_dl"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line.

    Args:
        argv: Arguments without the program name, or None for ``sys.argv``.

    Returns:
        Namespace with csv, out, models, epochs, device and log_txt.
    """
    parser = argparse.ArgumentParser(description="Lab 3: train and compare 8 DDoS detectors.")
    parser.add_argument("--csv", type=Path, default=common.DEFAULT_CSV, help="input CSV")
    parser.add_argument("--out", type=Path, default=common.DEFAULT_OUT, help="output root")
    parser.add_argument("--models", nargs="+", choices=ALL_KEYS, default=ALL_KEYS,
                        help="subset of models (run in registry order)")
    parser.add_argument("--epochs", type=int, default=None,
                        help="override the maximum epochs of all DL models "
                             "(default: each model's own MAX_EPOCHS)")
    parser.add_argument("--device", choices=DEVICE_CHOICES, default="auto",
                        help="torch device of the DL models (auto = cuda if available)")
    parser.add_argument("--log-txt", type=Path, default=None, dest="log_txt",
                        help="write one self-contained plain-text report (for sharing)")
    args = parser.parse_args(argv)
    if args.epochs is not None and args.epochs < 1:
        parser.error("--epochs must be >= 1")
    return args


def resolve_device(keys: list[str], requested: str) -> str | None:
    """Resolve ``--device``; torch is only imported when a DL model is selected.

    Args:
        keys: Selected model keys.
        requested: "auto", "cpu" or "cuda".

    Returns:
        "cpu" or "cuda", or None if no DL model is selected.
    """
    if not any(k in DL_KEYS for k in keys):
        return None
    # Lazy import keeps ``--models gnb`` free of torch.
    dl_common = importlib.import_module("dl.dl_common")
    return dl_common.resolve_device(requested)


def epoch_limits(keys: list[str], override: int | None) -> dict[str, int]:
    """Return the effective maximum epochs of every selected DL model.

    Args:
        keys: Selected model keys.
        override: ``--epochs`` value or None.

    Returns:
        {key: max epochs}, empty if no DL model is selected.
    """
    limits = {}
    for key in (k for k in DL_KEYS if k in keys):
        # Safe import: resolve_device already loaded torch for any DL selection.
        module = importlib.import_module(_module_name(key))
        # "is None", not "or": an explicit override is honoured as given (0 is rejected earlier).
        limits[key] = module.MAX_EPOCHS if override is None else override
    return limits


def run_models(keys: list[str], splits: common.DataSplits, epochs: int | None,
               device: str = "cpu") -> list[common.ModelResult]:
    """Train the selected models in registry order (ML, then DL).

    Args:
        keys: Selected model keys.
        splits: Shared data splits.
        epochs: DL epoch override, or None for each model's MAX_EPOCHS (ignored by ML models).
        device: Torch device of the DL models (ignored by ML models).

    Returns:
        One ModelResult per model.
    """
    results = []
    for key in (k for k in ALL_KEYS if k in keys):
        # Lazy import: torch is only loaded when a DL model is selected.
        module = importlib.import_module(_module_name(key))
        log.info("running %s", module.NAME)
        res = module.run(splits, epochs, device) if key in DL_KEYS else module.run(splits)
        log.info("%s: train %.2f s, predict %.3f s", res.name, res.train_time_s, res.predict_time_s)
        results.append(res)
    return results


def _write_json(data: Any, path: Path) -> None:
    """Write a JSON file with indentation, creating the directory.

    Args:
        data: JSON-serialisable object.
        path: Target file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=JSON_INDENT) + "\n", encoding="utf-8")


def _pipeline(args: argparse.Namespace, device: str | None) -> tuple[Any, list, dict]:
    """Preprocess, train, evaluate and write all outputs.

    Args:
        args: Parsed arguments.
        device: Resolved torch device or None.

    Returns:
        (preprocess summary, model results, metrics).
    """
    out = args.out
    splits, summary = preprocess.preprocess(args.csv)
    _write_json(summary, out / "metrics" / "preprocess_summary.json")
    results = run_models(args.models, splits, args.epochs, device or "cpu")
    metrics = evaluate.evaluate_all(results, splits)
    _write_json(metrics, out / "metrics" / "metrics.json")
    for key, entry in metrics.items():
        log.info("%s test F1 = %.4f", key, entry["test"]["f1"])
    comparison.run_comparison(results, metrics, out)
    roc_curves.plot_roc(results, splits.y_test, out)
    comparison.write_figure_index(out)
    log.info("test comparison:\n%s", comparison.build_table(metrics, "test").to_string(index=False))
    return summary, results, metrics


def main(argv: list[str] | None = None) -> int:
    """Run the whole pipeline.

    Args:
        argv: Command-line arguments, or None for ``sys.argv``.

    Returns:
        Exit code 0.
    """
    args = parse_args(argv)
    common.setup_logging(args.out)
    device = resolve_device(args.models, args.device)
    handler = None
    if args.log_txt:
        header = run_report.header_text(sys.argv, device)
        config = run_report.config_text(args.csv, args.models,
                                        epoch_limits(args.models, args.epochs))
        run_report.start_report(args.log_txt, header, config)
        handler = common.add_text_log(args.log_txt)
    log.info("DL device: %s", device or "n/a")
    try:
        summary, results, metrics = _pipeline(args, device)
    finally:
        # Always detach, or repeated in-process calls would leak the file handle.
        if handler:
            common.remove_text_log(handler)
    if args.log_txt:
        run_report.finish_report(args.log_txt, args.out, summary, results, metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
