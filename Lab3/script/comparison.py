"""Comparison tables and the figure index (Task 3: "Generate comparison table").

Builds the per-split tables (csv, md, tex, image), drives the chart modules and
writes ``figures/INDEX.md`` so the user can pick figures (decision D4).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

import common
import plots_confusion
import plots_metrics
import plots_training
from figure_index import FIGURE_CATALOG, write_figure_index

# Re-exported: the catalog and index writer live in figure_index.py (module size limit).
__all__ = ["FIGURE_CATALOG", "write_figure_index", "build_table", "save_table",
           "plot_table_image", "run_comparison", "table_markdown"]

SCORE_COLUMNS = ["Accuracy", "Precision", "Recall", "F1", "Macro-F1", "ROC-AUC"]
COLUMNS = ["Model", "Family", *SCORE_COLUMNS, "TP", "TN", "FP", "FN", "Train time (s)",
           "Predict time (s)"]
TIME_COLUMNS = ["Train time (s)", "Predict time (s)"]
SCORE_KEYS = ["accuracy", "precision", "recall", "f1", "macro_f1", "roc_auc"]
SCORE_DECIMALS, TIME_DECIMALS = 4, 3   # scores as decimals (user decision); times need fewer
SPLITS = ("test", "val")
TABLE_FONT = 11
TABLE_ROW_SCALE = 1.9
TABLE_ROW_H = 0.32                     # inches per table row
TABLE_TITLE_PAD = 36                   # points between the table and its title
TABLE_HEADER_H = 0.7                   # inches for the header row and title
LATEX_NOTE = ("% booktabs table (4-decimal scores, 3-decimal times). Wide: wrap it in\n"
              "% \\resizebox{\\textwidth}{!}{ ... } and \\usepackage{booktabs}.\n")
TABLE_COL_W = 1.05                     # inches per column of the image table
HEADER_COLOR = "#D9E2EC"

def build_table(metrics: dict, split: str) -> pd.DataFrame:
    """Build the comparison table of one split, sorted by F1 (descending).

    Args:
        metrics: Output of ``evaluate_all``.
        split: "test" or "val".

    Returns:
        DataFrame with the columns of CLAUDE.md 5; scores rounded to 4 decimals.
    """
    rows = []
    # Sort on the raw F1 first: two models equal after rounding must keep their true order.
    # sorted() is stable, so exact ties keep run order.
    ordered = sorted(metrics.values(), key=lambda e: e[split]["f1"], reverse=True)
    for entry in ordered:
        part = entry[split]
        scores = [round(part[k], SCORE_DECIMALS) for k in SCORE_KEYS]
        counts = [part[k] for k in ("tp", "tn", "fp", "fn")]
        rows.append([entry["name"], entry["family"], *scores, *counts,
                     round(entry["train_time_s"], TIME_DECIMALS),
                     round(entry["predict_time_s"], TIME_DECIMALS)])
    return pd.DataFrame(rows, columns=COLUMNS)


def _formatters() -> dict[str, str]:
    """Return per-column format strings for the md/tex/image output.

    Returns:
        Mapping column -> format spec such as ".4f".
    """
    spec = {c: f".{SCORE_DECIMALS}f" for c in SCORE_COLUMNS}
    spec.update({c: f".{TIME_DECIMALS}f" for c in TIME_COLUMNS})
    return spec


def table_markdown(df: pd.DataFrame) -> str:
    """Render a table as markdown with 4-decimal scores and 3-decimal times.

    Args:
        df: Table from ``build_table``.

    Returns:
        Markdown text (no trailing newline); shared by the .md export and the text report.
    """
    spec = _formatters()
    return df.to_markdown(index=False, floatfmt=[spec.get(c, "g") for c in df.columns])


def save_table(df: pd.DataFrame, metrics_dir: Path, stem: str) -> None:
    """Write ``stem.csv``, ``stem.md`` and ``stem.tex`` (rounded values, as in the table).

    The csv stays numeric (scores rounded to 4, times to 3 decimals); md and tex are formatted
    with fixed decimals. The tex is booktabs style and should be wrapped in
    ``\\resizebox{\\textwidth}{!}{...}`` by the report.

    Args:
        df: Table from ``build_table``.
        metrics_dir: Target directory (created if missing).
        stem: File stem, e.g. "comparison_test".
    """
    metrics_dir.mkdir(parents=True, exist_ok=True)
    spec = _formatters()
    df.to_csv(metrics_dir / f"{stem}.csv", index=False)
    (metrics_dir / f"{stem}.md").write_text(table_markdown(df) + "\n", encoding="utf-8")
    formatters = {c: f"{{:{s}}}".format for c, s in spec.items()}
    # The comment header tells the report author how to fit the 14 columns on a page.
    (metrics_dir / f"{stem}.tex").write_text(
        LATEX_NOTE + df.to_latex(index=False, formatters=formatters), encoding="utf-8")


def plot_table_image(df: pd.DataFrame, fig_dir: Path) -> None:
    """Render the table as an image (``comparison_table``).

    Args:
        df: Table from ``build_table``.
        fig_dir: Figure directory.
    """
    spec = _formatters()
    cells = [[format(v, spec[c]) if c in spec else str(v) for c, v in row.items()]
             for row in df.to_dict("records")]
    fig = Figure(figsize=(TABLE_COL_W * len(df.columns), TABLE_HEADER_H + TABLE_ROW_H * len(df)))
    ax = fig.add_subplot(1, 1, 1)
    ax.axis("off")
    table = ax.table(cellText=cells, colLabels=list(df.columns), loc="center", cellLoc="center",
                     colColours=[HEADER_COLOR] * len(df.columns))
    table.auto_set_font_size(False)
    table.set_fontsize(TABLE_FONT)
    table.auto_set_column_width(list(range(len(df.columns))))
    table.scale(1, TABLE_ROW_SCALE)
    ax.set_title("Model comparison on the test set (sorted by F1)", fontsize=TABLE_FONT + 3,
                 pad=TABLE_TITLE_PAD)
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
