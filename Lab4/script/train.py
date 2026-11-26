"""Train, select, export and verify the kernel DT and XGBoost models (CLAUDE.md 4.3, 5.4).

Metrics port: ``compute_metrics`` is copied from ``../Lab3/script/evaluate.py`` (never imported).
Depths are chosen on the validation split only; the test split is scored after they are fixed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

import common
import export_model as em
import kmodel
import preprocess as pp
import replay
import report

log = logging.getLogger(__name__)

THRESHOLD = 0.5
HASH_CHUNK = 1 << 20
N_VECTORS_PER_CLASS = common.N_TEST_VECS // 2


def compute_metrics(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, float | int]:
    """Scores and confusion matrix for one split (DDoS = positive; ported from Lab 3).

    Args:
        y_true: Labels (1 = DDoS).
        y_score: P(DDoS) per sample.

    Returns:
        Dict with accuracy, precision, recall, f1, macro_f1, roc_auc and tn/fp/fn/tp.
    """
    # Strict ">" matches sklearn predict: an exact 0.5 is BENIGN.
    y_pred = (y_score > THRESHOLD).astype(np.int64)
    # labels=[0, 1] keeps a 2x2 matrix even when a class is absent from y_pred.
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def select_depth(val_f1: dict[int, float], tol: float) -> int:
    """Smallest depth whose validation F1 is within tol of the best.

    Args:
        val_f1: {depth: validation F1}.
        tol: Allowed gap to the best F1.

    Returns:
        The chosen depth.
    """
    best = max(val_f1.values())
    # 1e-12 absorbs float error when the gap is exactly tol.
    return min(d for d, f in val_f1.items() if f >= best - tol - 1e-12)


def fit_dt(splits: pp.KernelSplits, depth: int) -> DecisionTreeClassifier:
    """Fit the Decision Tree on the raw training features.

    Args:
        splits: Kernel splits.
        depth: max_depth.

    Returns:
        Fitted tree.
    """
    return DecisionTreeClassifier(max_depth=depth, random_state=common.SEED).fit(
        splits.x_train, splits.y_train)


def fit_xgb(splits: pp.KernelSplits, depth: int) -> XGBClassifier:
    """Fit XGBoost with exactly XGB_TREES rounds (no early stopping).

    Args:
        splits: Kernel splits.
        depth: max_depth.

    Returns:
        Fitted classifier.
    """
    model = XGBClassifier(n_estimators=common.XGB_TREES, max_depth=depth,
                          learning_rate=common.XGB_LR, tree_method="hist", eval_metric="logloss",
                          n_jobs=-1, random_state=common.SEED)
    return model.fit(splits.x_train, splits.y_train, verbose=False)


def _timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    """Run fn and time it.

    Args:
        fn: Zero-argument callable.

    Returns:
        (result, seconds).
    """
    start = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - start


def _score(model: Any, x: np.ndarray) -> np.ndarray:
    """P(DDoS) of a fitted float model.

    Args:
        model: sklearn-style classifier.
        x: Features.

    Returns:
        1-D score array.
    """
    return model.predict_proba(x)[:, 1]


def _evaluate(name: str, score_fn: Callable[[np.ndarray], np.ndarray], splits: pp.KernelSplits,
              train_s: float) -> dict[str, Any]:
    """Score one model on val and test.

    Args:
        name: Display name.
        score_fn: Maps features to P(DDoS).
        splits: Kernel splits.
        train_s: Training time to report.

    Returns:
        {name, val, test, train_time_s, predict_time_s} (predict time covers the test split).
    """
    val = compute_metrics(splits.y_val, score_fn(splits.x_val))
    score, predict_s = _timed(lambda: score_fn(splits.x_test))
    return {"name": name, "val": val, "test": compute_metrics(splits.y_test, score),
            "train_time_s": train_s, "predict_time_s": predict_s}


def _int_scores(kmodel_dict: dict[str, Any]) -> tuple[Callable, Callable]:
    """Score functions of the integer DT and XGB (sigmoid of the margin, so 0 maps to 0.5).

    Args:
        kmodel_dict: Kernel model.

    Returns:
        (dt_score_fn, xgb_score_fn) taking raw float features.
    """
    def dt_fn(x: np.ndarray) -> np.ndarray:
        """Integer DT verdicts as scores."""
        return em.kernel_predictions(kmodel_dict, em.to_int_features(x))[0].astype(np.float64)

    def xgb_fn(x: np.ndarray) -> np.ndarray:
        """Integer XGB margin as probability."""
        margin = em.kernel_predictions(kmodel_dict, em.to_int_features(x))[1]
        return 1.0 / (1.0 + np.exp(-margin / (1 << common.LEAF_SHIFT)))
    return dt_fn, xgb_fn


def _sha256(path: Path) -> str:
    """Hash a file in chunks.

    Args:
        path: File to hash.

    Returns:
        Hex digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(HASH_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _select(kind: str, fit: Callable, depths: tuple[int, ...], splits: pp.KernelSplits,
            selection: dict[str, Any]) -> tuple[Any, int, float]:
    """Fit every candidate depth, pick one on validation F1 only.

    Args:
        kind: "dt" or "xgb" (key in ``selection``).
        fit: fit_dt or fit_xgb.
        depths: Candidate depths.
        splits: Kernel splits (only x_val / y_val are scored here).
        selection: depth_selection.json content, updated in place.

    Returns:
        (selected model, selected depth, its training time).
    """
    fitted = {d: _timed(lambda d=d: fit(splits, d)) for d in depths}
    val_f1 = {d: compute_metrics(splits.y_val, _score(m, splits.x_val))["f1"]
              for d, (m, _) in fitted.items()}
    depth = select_depth(val_f1, common.DEPTH_F1_TOL)
    selection[kind] = {"val_f1": {str(d): f for d, f in val_f1.items()}, "selected": depth}
    log.info("%s val F1 by depth %s -> %d", kind, val_f1, depth)
    return fitted[depth][0], depth, fitted[depth][1]


def _export(dt: Any, xgb: Any, dt_depth: int, xgb_depth: int,
            args: argparse.Namespace) -> dict[str, Any]:
    """Export, validate and save the kernel model.

    Args:
        dt: Selected tree.
        xgb: Selected XGBClassifier.
        dt_depth: DT depth (meta).
        xgb_depth: XGB depth (meta).
        args: Parsed CLI arguments.

    Returns:
        The kernel model dict.
    """
    kdict = em.build_kernel_model(em.export_dt(dt), em.export_xgb(xgb), {
        "dt_depth": dt_depth, "xgb_depth": xgb_depth, "csv_sha256": _sha256(args.csv)})
    kmodel.validate(kdict)
    kmodel.save(kdict, args.models_dir / common.KERNEL_MODEL_PATH.name)
    return kdict


def _write_pool(splits: pp.KernelSplits, models_dir: Path) -> None:
    """Write the replay pool (rebuildable test-split flows of both classes, CLAUDE.md D8).

    Args:
        splits: Kernel splits (only the test split is used).
        models_dir: Output directory.
    """
    frame = pd.DataFrame(splits.x_test, columns=splits.feature_names)
    pool = replay.build_pool(frame, splits.y_test)
    (models_dir / common.REPLAY_POOL_PATH.name).write_text(json.dumps(pool), encoding="utf-8")
    log.info("replay pool: %s", dict(collections.Counter(f["label"] for f in pool)))


def _report(models: tuple[Any, Any], kdict: dict[str, Any], splits: pp.KernelSplits,
            train_s: tuple[float, float], args: argparse.Namespace) -> None:
    """Score on val and test, write metrics, parity and test vectors.

    Args:
        models: (selected DT, selected XGBClassifier).
        kdict: Kernel model.
        splits: Kernel splits.
        train_s: (DT, XGB) training times.
        args: Parsed CLI arguments.
    """
    dt, xgb = models
    metrics_dir = args.out / "metrics"
    int_dt, int_xgb = _int_scores(kdict)
    results = {"dt": _evaluate("Decision Tree", lambda x: _score(dt, x), splits, train_s[0]),
               "xgb": _evaluate("XGBoost (20 trees)", lambda x: _score(xgb, x), splits, train_s[1]),
               "dt_kernel": _evaluate("Decision Tree (integer)", int_dt, splits, train_s[0]),
               "xgb_kernel": _evaluate("XGBoost (integer)", int_xgb, splits, train_s[1])}
    report.dump_json(results, metrics_dir / "metrics.json")
    report.write_tables(results, metrics_dir)
    report.write_importance(dt, xgb, splits.feature_names, metrics_dir / "feature_importance.md")
    report.write_parity(em.parity(dt, xgb, kdict, splits.x_test, splits.y_test), metrics_dir)
    vectors = em.sample_test_vectors(em.to_int_features(splits.x_test), splits.y_test, kdict,
                                     N_VECTORS_PER_CLASS, common.SEED)
    report.dump_json(vectors, args.models_dir / common.TEST_VECTORS_PATH.name)
    _write_pool(splits, args.models_dir)
    log.info("test metrics:\n%s", (metrics_dir / "comparison_test.md").read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    """Run the whole offline pipeline.

    Args:
        argv: Command-line arguments (default sys.argv).

    Returns:
        0 on success.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=common.DEFAULT_CSV)
    ap.add_argument("--out", type=Path, default=common.DEFAULT_OUT)
    ap.add_argument("--models-dir", type=Path, default=common.MODELS_DIR)
    args = ap.parse_args(argv)
    common.setup_logging(args.out)
    metrics_dir = args.out / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    splits, summary = pp.preprocess(args.csv)
    report.dump_json(summary, metrics_dir / "preprocess_summary.json")
    selection: dict[str, Any] = {"tolerance": common.DEPTH_F1_TOL}
    dt, dt_depth, dt_s = _select("dt", fit_dt, common.DT_DEPTHS, splits, selection)
    xgb, xgb_depth, xgb_s = _select("xgb", fit_xgb, common.XGB_DEPTHS, splits, selection)
    report.dump_json(selection, metrics_dir / "depth_selection.json")

    kdict = _export(dt, xgb, dt_depth, xgb_depth, args)
    # Depths are fixed: the test split is scored from here on.
    _report((dt, xgb), kdict, splits, (dt_s, xgb_s), args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
