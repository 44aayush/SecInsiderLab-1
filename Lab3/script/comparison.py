"""Comparison tables and the figure index (Task 3: "Generate comparison table").

Builds the per-split tables (csv, md, tex, image), drives the chart modules and
writes ``figures/INDEX.md`` so the user can pick figures (decision D4).
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

import common
import plots_confusion
import plots_metrics
import plots_training

log = logging.getLogger(__name__)

SCORE_COLUMNS = ["Accuracy", "Precision", "Recall", "F1", "Macro-F1", "ROC-AUC"]
COLUMNS = ["Model", "Family", *SCORE_COLUMNS, "TP", "TN", "FP", "FN", "Train time (s)",
           "Predict time (s)"]
TIME_COLUMNS = ["Train time (s)", "Predict time (s)"]
SCORE_KEYS = ["accuracy", "precision", "recall", "f1", "macro_f1", "roc_auc"]
SCORE_DECIMALS, TIME_DECIMALS = 4, 3   # scores as decimals (user decision); times need fewer
SPLITS = ("test", "val")
TABLE_FONT = 11
TABLE_ROW_SCALE = 1.9
TABLE_COL_W = 1.05                     # inches per column of the image table
HEADER_COLOR = "#D9E2EC"
CONFUSION_PATTERN = "confusion_<key>"

FIGURE_CATALOG: dict[str, tuple[str, str]] = {
    "metrics_bar_grouped": ("grouped bars", "Accuracy, Precision, Recall and F1 per model"),
    "metrics_small_multiples": ("small multiples, sorted bars", "ranking per metric"),
    "metrics_heatmap": ("annotated heatmap", "everything at a glance"),
    "metrics_radar": ("radar chart", "the profile of each model"),
    "metrics_dot": ("Cleveland dot plot", "a compact comparison"),
    "errors_bar": ("grouped bars, log y-axis", "FP and FN, where near-perfect models differ"),
    "time_bar": ("horizontal bars, log x-axis", "train and predict cost"),
    "comparison_table": ("table image", "a slide-ready test table"),
    "confusion_grid_counts": ("confusion heatmap grid, counts", "all models side by side"),
    "confusion_grid_normalized": ("confusion heatmap grid, row-normalised rates",
                                  "rates (0-1, 4 decimals) instead of counts"),
    CONFUSION_PATTERN: ("single confusion heatmap", "one model on one slide"),
    "roc_test": ("ROC curves, full axes", "the Task 3 ROC figure"),
    "roc_test_zoom": ("ROC curves, FPR 0-0.05, TPR 0.95-1", "separates the near-perfect models"),
    "roc_test_logx": ("ROC curves, log-scale FPR", "low false-alarm behaviour"),
    "roc_grid": ("ROC small multiples", "each curve on its own"),
    "roc_test_ml": ("ROC curves, ML only", "the family comparison"),
    "roc_test_dl": ("ROC curves, DL only", "the family comparison"),
    "dl_history_overlay": ("line chart", "validation loss of all DL models, convergence compared"),
    "dl_history_grid": ("line chart grid", "train and val loss per DL model, best epoch marked"),
}


def build_table(metrics: dict, split: str) -> pd.DataFrame:
    """Build the comparison table of one split, sorted by F1 (descending).

    Args:
        metrics: Output of ``evaluate_all``.
        split: "test" or "val".

    Returns:
        DataFrame with the columns of CLAUDE.md 5; scores rounded to 4 decimals.
    """
    rows = []
    for entry in metrics.values():
        part = entry[split]
        scores = [round(part[k], SCORE_DECIMALS) for k in SCORE_KEYS]
        counts = [part[k] for k in ("tp", "tn", "fp", "fn")]
        rows.append([entry["name"], entry["family"], *scores, *counts,
                     round(entry["train_time_s"], TIME_DECIMALS),
                     round(entry["predict_time_s"], TIME_DECIMALS)])
    # Sort on the unrounded-equivalent F1; ties keep run order (stable sort).
    return pd.DataFrame(rows, columns=COLUMNS).sort_values("F1", ascending=False,
                                                           kind="stable").reset_index(drop=True)


def _formatters() -> dict[str, str]:
    """Return per-column format strings for the md/tex/image output.

    Returns:
        Mapping column -> format spec such as ".4f".
    """
    spec = {c: f".{SCORE_DECIMALS}f" for c in SCORE_COLUMNS}
    spec.update({c: f".{TIME_DECIMALS}f" for c in TIME_COLUMNS})
    return spec


def save_table(df: pd.DataFrame, metrics_dir: Path, stem: str) -> None:
    """Write ``stem.csv``, ``stem.md`` and ``stem.tex`` (rounded values, as in the table).

    Args:
        df: Table from ``build_table``.
        metrics_dir: Target directory (created if missing).
        stem: File stem, e.g. "comparison_test".
    """
    metrics_dir.mkdir(parents=True, exist_ok=True)
    spec = _formatters()
    df.to_csv(metrics_dir / f"{stem}.csv", index=False)
    floatfmt = [spec.get(c, "g") for c in df.columns]
    (metrics_dir / f"{stem}.md").write_text(df.to_markdown(index=False, floatfmt=floatfmt) + "\n",
                                            encoding="utf-8")
    formatters = {c: f"{{:{s}}}".format for c, s in spec.items()}
    (metrics_dir / f"{stem}.tex").write_text(df.to_latex(index=False, formatters=formatters),
                                             encoding="utf-8")


def plot_table_image(df: pd.DataFrame, fig_dir: Path) -> None:
    """Render the table as an image (``comparison_table``).

    Args:
        df: Table from ``build_table``.
        fig_dir: Figure directory.
    """
    spec = _formatters()
    cells = [[format(v, spec[c]) if c in spec else str(v) for c, v in row.items()]
             for row in df.to_dict("records")]
    fig = Figure(figsize=(TABLE_COL_W * len(df.columns), 1 + 0.5 * len(df)), layout="constrained")
    ax = fig.add_subplot(1, 1, 1)
    ax.axis("off")
    table = ax.table(cellText=cells, colLabels=list(df.columns), loc="center", cellLoc="center",
                     colColours=[HEADER_COLOR] * len(df.columns))
    table.auto_set_font_size(False)
    table.set_fontsize(TABLE_FONT)
    table.auto_set_column_width(list(range(len(df.columns))))
    table.scale(1, TABLE_ROW_SCALE)
    ax.set_title("Model comparison on the test set (sorted by F1)", fontsize=TABLE_FONT + 3)
    common.save_figure(fig, fig_dir / "comparison_table")


def run_comparison(results: list[common.ModelResult], metrics: dict, out_dir: Path) -> None:
    """Write the tables, the table image and all metric/confusion/training charts.

    Args:
        results: Model results in run order.
        metrics: Output of ``evaluate_all``.
        out_dir: Output root.
    """
    for split in SPLITS:
        save_table(build_table(metrics, split), out_dir / "metrics", f"comparison_{split}")
    fig_dir = out_dir / "figures"
    plot_table_image(build_table(metrics, "test"), fig_dir)
    plots_metrics.plot_all(metrics, fig_dir)
    plots_confusion.plot_all(metrics, fig_dir)
    plots_training.plot_all(results, fig_dir)


def _existing_entries(fig_dir: Path) -> list[tuple[str, str, str]]:
    """List (stem, chart type, purpose) of the catalog stems present as PNG.

    Args:
        fig_dir: Figure directory.

    Returns:
        Entries in catalog order; the confusion pattern expands to one entry per model key.
    """
    entries = []
    for stem, (chart, purpose) in FIGURE_CATALOG.items():
        names = [stem]
        if stem == CONFUSION_PATTERN:
            names = [f"confusion_{k}" for k in common.MODEL_COLORS]
        entries += [(n, chart, purpose) for n in names if (fig_dir / f"{n}.png").exists()]
    return entries


def write_figure_index(out_dir: Path) -> None:
    """Write ``figures/INDEX.md`` listing only the figures that exist.

    Args:
        out_dir: Output root.
    """
    fig_dir = out_dir / "figures"
    entries = _existing_entries(fig_dir)
    lines = ["# Figure index", "",
             "Pick the figures for the report and the deck. Every figure also exists as PDF.", "",
             "| Stem | Chart type | Purpose | PNG |", "|---|---|---|---|"]
    lines += [f"| `{s}` | {c} | {p} | [{s}.png]({s}.png) |" for s, c, p in entries]
    fig_dir.mkdir(parents=True, exist_ok=True)
    (fig_dir / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("figure index lists %d figures", len(entries))
