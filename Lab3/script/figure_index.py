"""Tiered figure catalog and ``figures/INDEX.md`` writer (Task 3, decision D4).

Every figure belongs to one tier that says how many figures a report needs:
the user picks figures from the index, and the report and the deck reuse them.
Split out of ``comparison.py`` to keep that module short.
"""
from __future__ import annotations

import logging
from pathlib import Path

import common

log = logging.getLogger(__name__)

CONFUSION_PATTERN = "confusion_<key>"

# tier number -> (heading, guidance on when to use it)
TIERS: dict[int, tuple[str, str]] = {
    1: ("Tier 1 - Core", "a short report uses only these"),
    2: ("Tier 2 - Recommended additions",
        "a full 10-15 page report uses Tier 1 + Tier 2"),
    3: ("Tier 3 - Alternatives",
        "swap one in for the Tier 1/2 figure named under 'alternative to'; not in addition"),
    4: ("Tier 4 - Appendix (per-model detail)", "one confusion matrix per model run"),
}

# Header lines of INDEX.md: how many figures per tier and when to use it.
TIER_SUMMARY = [
    "- Tier 1 Core (7 figures): short report. Slides: Tier 1 minus dl_history_grid.",
    "- Tier 2 Recommended additions (+5): full report = Tier 1 + Tier 2 (12).",
    "- Tier 3 Alternatives: swap in for a Tier 1/2 figure; not in addition.",
    "- Tier 4 Appendix: one confusion matrix per model run.",
]

# stem -> (tier, chart type, purpose); tier 3 purposes name the figure they replace.
FIGURE_CATALOG: dict[str, tuple[int, str, str]] = {
    "comparison_table": (1, "table image", "a slide-ready test table"),
    "metrics_bar_grouped": (1, "grouped bars", "Accuracy, Precision, Recall and F1 per model"),
    "errors_bar": (1, "grouped bars, log y-axis",
                   "FP and FN, where near-perfect models differ"),
    "roc_test": (1, "ROC curves, full axes", "the Task 3 ROC figure"),
    "roc_test_zoom": (1, "ROC curves, FPR 0-0.05, TPR 0.95-1",
                      "separates the near-perfect models"),
    "confusion_grid_counts": (1, "confusion heatmap grid, counts", "all models side by side"),
    "dl_history_grid": (1, "line chart grid",
                        "train and val loss per DL model, best epoch marked"),
    "metrics_heatmap": (2, "annotated heatmap", "everything at a glance"),
    "roc_test_logx": (2, "ROC curves, log-scale FPR", "low false-alarm behaviour"),
    "time_bar": (2, "horizontal bars, log x-axis", "train and predict cost"),
    "confusion_grid_normalized": (2, "confusion heatmap grid, row-normalised rates",
                                  "rates (0-1, 4 decimals) instead of counts"),
    "dl_history_overlay": (2, "line chart",
                           "validation loss of all DL models, convergence compared"),
    "metrics_small_multiples": (3, "small multiples, sorted bars",
                                "ranking per metric; alternative to metrics_bar_grouped"),
    "metrics_radar": (3, "radar chart",
                      "the profile of each model; alternative to metrics_heatmap"),
    "metrics_dot": (3, "Cleveland dot plot",
                    "a compact comparison; alternative to metrics_bar_grouped"),
    "roc_grid": (3, "ROC small multiples", "each curve on its own; alternative to roc_test"),
    "roc_test_ml": (3, "ROC curves, ML only",
                    "the family comparison; alternative to roc_test_zoom"),
    "roc_test_dl": (3, "ROC curves, DL only",
                    "the family comparison; alternative to roc_test_zoom"),
    CONFUSION_PATTERN: (4, "single confusion heatmap", "one model on one slide"),
}


def _existing_entries(fig_dir: Path) -> list[tuple[int, str, str, str]]:
    """List (tier, stem, chart type, purpose) of the catalog stems present as PNG.

    Args:
        fig_dir: Figure directory.

    Returns:
        Entries in catalog order; the confusion pattern expands to one entry per model key.
    """
    entries = []
    for stem, (tier, chart, purpose) in FIGURE_CATALOG.items():
        names = [stem]
        if stem == CONFUSION_PATTERN:
            names = [f"confusion_{k}" for k in common.MODEL_COLORS]
        entries += [(tier, n, chart, purpose) for n in names if (fig_dir / f"{n}.png").exists()]
    return entries


def _tier_table(tier: int, entries: list[tuple[int, str, str, str]]) -> list[str]:
    """Render the heading and table of one tier (empty list if it has no figures).

    Args:
        tier: Tier number, a key of ``TIERS``.
        entries: Output of ``_existing_entries``.

    Returns:
        Markdown lines.
    """
    rows = [e for e in entries if e[0] == tier]
    if not rows:
        return []
    title, guidance = TIERS[tier]
    lines = [f"## {title} ({len(rows)} figures)", "", f"_{guidance}._", "",
             "| Figure | Chart type | Purpose |", "|---|---|---|"]
    lines += [f"| [{s}]({s}.png) | {c} | {p} |" for _, s, c, p in rows]
    return lines + [""]


def write_figure_index(out_dir: Path) -> None:
    """Write ``figures/INDEX.md``: one table per tier, only figures that exist.

    Args:
        out_dir: Output root.
    """
    fig_dir = out_dir / "figures"
    entries = _existing_entries(fig_dir)
    lines = ["# Figure index", "",
             "Pick the figures for the report and the deck. Every figure also exists as PDF.",
             "", *TIER_SUMMARY, ""]
    for tier in TIERS:
        lines += _tier_table(tier, entries)
    lines.append(f"Total: {len(entries)} figures listed.")
    fig_dir.mkdir(parents=True, exist_ok=True)
    (fig_dir / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("figure index lists %d figures", len(entries))
