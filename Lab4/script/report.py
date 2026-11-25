"""Writers for the offline training outputs: comparison tables, importances, parity files.

Split from ``train.py`` to keep both modules short. Host only.
"""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

TABLE_COLS = ("accuracy", "precision", "recall", "f1", "macro_f1", "roc_auc", "tp", "tn", "fp",
              "fn", "train_time_s", "predict_time_s")
TABLE_HEAD = ("Model", "Accuracy", "Precision", "Recall", "F1", "Macro-F1", "ROC-AUC", "TP", "TN",
              "FP", "FN", "Train time (s)", "Predict time (s)")
PARITY_DT_MIN, PARITY_XGB_MIN, PARITY_MARGIN_TOL = 1.0, 0.9999, 1e-3  # CLAUDE.md 5.2


def _table(results: dict[str, dict[str, Any]], split: str) -> list[list[Any]]:
    """Rows of the comparison table for one split.

    Args:
        results: metrics.json content.
        split: "val" or "test".

    Returns:
        One row per model: name then the TABLE_COLS values.
    """
    return [[r["name"], *[{**r[split], "train_time_s": r["train_time_s"],
                           "predict_time_s": r["predict_time_s"]}[c] for c in TABLE_COLS]]
            for r in results.values()]


def write_tables(results: dict[str, dict[str, Any]], metrics_dir: Path) -> None:
    """Write comparison_{val,test}.{csv,md}.

    Args:
        results: metrics.json content.
        metrics_dir: Output directory.
    """
    for split in ("val", "test"):
        rows = [[f"{v:.4f}" if isinstance(v, float) else v for v in row]
                for row in _table(results, split)]
        with (metrics_dir / f"comparison_{split}.csv").open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows([TABLE_HEAD, *rows])
        lines = [TABLE_HEAD, ["---"] * len(TABLE_HEAD), *rows]
        text = "\n".join("| " + " | ".join(str(c) for c in line) + " |" for line in lines)
        (metrics_dir / f"comparison_{split}.md").write_text(text + "\n", encoding="utf-8")


def write_importance(dt: Any, xgb: Any, names: list[str], path: Path) -> None:
    """Write feature_importance.md (DT impurity importance, XGB gain).

    Args:
        dt: Fitted tree.
        xgb: Fitted XGBClassifier.
        names: Feature names.
        path: Output file.
    """
    lines = ["| Feature | DT importance | XGB gain importance |", "|---|---|---|"]
    lines += [f"| {n} | {a:.4f} | {b:.4f} |"
              for n, a, b in zip(names, dt.feature_importances_, xgb.feature_importances_)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_parity(result: dict[str, Any], metrics_dir: Path) -> None:
    """Write parity.json and parity_mismatches.csv, and warn if the AC of CLAUDE.md 5.2 fails.

    Args:
        result: Output of ``em.parity`` (mismatch rows are removed from the JSON).
        metrics_dir: Output directory.
    """
    summary = {k: v for k, v in result.items() if k != "mismatches"}
    summary["ac_pass"] = bool(result["dt_agreement"] >= PARITY_DT_MIN
                              and result["xgb_agreement"] >= PARITY_XGB_MIN
                              and result["max_margin_abs_err"] <= PARITY_MARGIN_TOL)
    (metrics_dir / "parity.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    fields = ["row", "model", "label", "float", "kernel"]
    with (metrics_dir / "parity_mismatches.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result["mismatches"])
    if not summary["ac_pass"]:
        log.warning("PARITY AC FAILED: %s", summary)


def dump_json(obj: Any, path: Path) -> None:
    """Write indented JSON.

    Args:
        obj: JSON-serialisable object.
        path: Output file.
    """
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
