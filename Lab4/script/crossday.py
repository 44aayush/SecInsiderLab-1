"""Cross-day test: score the frozen kernel model on the Wednesday CSV (CLAUDE.md 2 D7, O14).

No retraining and no refitting. Cleaning drops inf/NaN rows and duplicate rows only (Lab 3 steps
2-4), never columns. BENIGN -> 0, every other label -> 1. Host only (numpy, pandas, sklearn).
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import common
import export_model as em
import kmodel
import preprocess as pp
import report
from train import compute_metrics

log = logging.getLogger(__name__)

DEFAULT_WED_CSV = common.LAB4_DIR / "Wednesday_dataset" / "Wednesday-workingHours.pcap_ISCX.csv"
DEFAULT_WED_OUT = common.LAB4_DIR / "Wednesday_dataset" / "outputs"
MODES = ("DT", "XGB", "ALL")
N_VECTORS_PER_CLASS = common.N_TEST_VECS // 2


def _counts(labels: pd.Series) -> dict[str, int]:
    """Count rows per label.

    Args:
        labels: Series of label strings.

    Returns:
        {label: count}.
    """
    return {str(k): int(v) for k, v in labels.value_counts().items()}


def binary_labels(labels: pd.Series) -> np.ndarray:
    """Map BENIGN to 0 and every other label to 1.

    Args:
        labels: Series of label strings.

    Returns:
        int64 array.
    """
    return (labels != common.NEGATIVE_LABEL).to_numpy(dtype=np.int64)


def clean_rows(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Drop inf/NaN rows and duplicate rows; no column is dropped.

    Args:
        raw: Output of ``preprocess.load_raw``.

    Returns:
        The cleaned frame (index reset) and the summary fragment.
    """
    df, summary = pp.drop_inf_nan_rows(raw)
    df, summary["duplicate_rows"] = pp.drop_duplicate_rows(df, common.DROP_DUPLICATES)
    df = df.reset_index(drop=True)
    summary["clean_shape"] = [len(df), df.shape[1] - 1]  # Label excluded
    summary["clean_class_counts"] = _counts(df[pp.LABEL_COL])
    return df, summary


def score(model: dict[str, Any], x_int: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Score every row with the integer model.

    Args:
        model: Kernel model.
        x_int: int64 features in kernel units.

    Returns:
        {mode: (verdict 0/1, score in [0, 1])} for DT, XGB and ALL; the XGB score is
        sigmoid(margin) and the ALL score is the smaller of the two, so ALL > 0.5 iff both agree.
    """
    dt, margin = em.kernel_predictions(model, x_int)
    p_xgb = 1.0 / (1.0 + np.exp(-margin / (1 << common.LEAF_SHIFT)))
    scores = {"DT": dt.astype(np.float64), "XGB": p_xgb, "ALL": np.minimum(dt, p_xgb)}
    verdicts = {"DT": dt, "XGB": (margin > 0).astype(np.int64)}
    verdicts["ALL"] = verdicts["DT"] & verdicts["XGB"]
    return {m: (verdicts[m], scores[m]) for m in MODES}


def mode_metrics(y: np.ndarray, scored: dict[str, tuple[np.ndarray, np.ndarray]]) -> dict[str, Any]:
    """Lab 3 metrics plus the BENIGN false-alarm rate per mode.

    Args:
        y: Binary labels.
        scored: Output of ``score``.

    Returns:
        {mode: metrics dict}.
    """
    out: dict[str, Any] = {}
    for mode, (_, s) in scored.items():
        m = compute_metrics(y, s)
        m["false_alarm_rate"] = m["fp"] / max(m["fp"] + m["tn"], 1)
        out[mode] = m
    return out


def per_label(labels: pd.Series, scored: dict[str, tuple[np.ndarray, np.ndarray]]) -> list[dict]:
    """Detections (predicted 1) and rate per original label and mode.

    Args:
        labels: Original label strings of the clean rows.
        scored: Output of ``score``.

    Returns:
        One dict per label (BENIGN first, then by size): label, n, detected_<M>, rate_<M>.
    """
    sizes = labels.value_counts()
    names = sorted(sizes.index, key=lambda lab: (lab != common.NEGATIVE_LABEL, -sizes[lab]))
    rows = []
    for lab in names:
        mask = (labels == lab).to_numpy()
        row: dict[str, Any] = {"label": lab, "n": int(mask.sum())}
        for mode in MODES:
            row[f"detected_{mode}"] = int(scored[mode][0][mask].sum())
            row[f"rate_{mode}"] = row[f"detected_{mode}"] / row["n"]
        rows.append(row)
    return rows


def write_table(rows: list[dict[str, Any]], stem: Path) -> None:
    """Write rows as ``<stem>.csv`` and ``<stem>.md`` (floats with 4 decimals).

    Args:
        rows: Non-empty list of dicts with the same keys.
        stem: Output path without suffix.
    """
    head = list(rows[0])
    body = [[f"{v:.4f}" if isinstance(v, float) else v for v in r.values()] for r in rows]
    with stem.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([head, *body])
    lines = [head, ["---"] * len(head), *body]
    text = "\n".join("| " + " | ".join(str(c) for c in line) + " |" for line in lines)
    stem.with_suffix(".md").write_text(text + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the cross-day test.

    Args:
        argv: Command-line arguments (default sys.argv).

    Returns:
        0 on success.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=DEFAULT_WED_CSV)
    ap.add_argument("--model-file", type=Path, default=common.KERNEL_MODEL_PATH)
    ap.add_argument("--out", type=Path, default=DEFAULT_WED_OUT)
    args = ap.parse_args(argv)
    common.setup_logging(args.out)
    model = kmodel.load(args.model_file)
    raw = pp.load_raw(args.csv)
    summary: dict[str, Any] = {"raw_shape": [int(n) for n in raw.shape],
                               "raw_class_counts": _counts(raw[pp.LABEL_COL])}
    df, part = clean_rows(raw)
    summary.update(part)
    report.dump_json(summary, args.out / "preprocess_summary.json")
    y = binary_labels(df[pp.LABEL_COL])
    x_int = em.to_int_features(pp.select_kernel_features(df).to_numpy(dtype="float64"))
    scored = score(model, x_int)
    metrics = mode_metrics(y, scored)
    report.dump_json(metrics, args.out / "metrics.json")
    write_table([{"mode": m, **v} for m, v in metrics.items()], args.out / "comparison")
    write_table(per_label(df[pp.LABEL_COL], scored), args.out / "per_label")
    vectors = em.sample_test_vectors(x_int, y, model, N_VECTORS_PER_CLASS, common.SEED)
    (args.out / "test_vectors.json").write_text(json.dumps(vectors), encoding="utf-8")
    log.info("per label:\n%s", (args.out / "per_label.md").read_text(encoding="utf-8"))
    log.info("comparison:\n%s", (args.out / "comparison.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
