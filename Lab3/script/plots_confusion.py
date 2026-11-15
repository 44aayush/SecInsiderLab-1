"""Confusion-matrix figures on the test split (Task 3, CLAUDE.md 5.1).

Writes ``confusion_grid_counts`` (raw counts), ``confusion_grid_normalized``
(row-normalised rates, 0-1 with 4 decimals) and one ``confusion_<key>`` per model.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

import common
from plot_utils import FONT_ANNOT, FONT_LABEL, FONT_TICK, FONT_TITLE, make_grid

log = logging.getLogger(__name__)

CLASS_LABELS = [common.NEGATIVE_LABEL, common.POSITIVE_LABEL]
CMAP = "Blues"
SINGLE_SIZE = 5.5
CELL_FONT = 14
RATE_DECIMALS = 4                  # row-normalised rates as 0.9999 (user decision)
PANEL_TITLES = {False: "counts", True: "row-normalised rates"}  # per-model figure panels
LIGHT_TEXT_FRACTION = 0.5          # cells darker than this share of the maximum get white text


def _matrix(entry: dict) -> np.ndarray:
    """Build the [[TN, FP], [FN, TP]] matrix of one model.

    Args:
        entry: One ``evaluate_all`` entry.

    Returns:
        2x2 int array of test counts.
    """
    test = entry["test"]
    return np.array([[test["tn"], test["fp"]], [test["fn"], test["tp"]]])


def _draw(ax: Axes, matrix: np.ndarray, title: str, normalized: bool) -> None:
    """Draw one annotated confusion heatmap.

    Args:
        ax: Target axes.
        matrix: 2x2 count matrix.
        title: Panel title.
        normalized: Show row-normalised rates (0-1) instead of counts.
    """
    shown = matrix
    if normalized:
        shown = matrix / np.maximum(matrix.sum(axis=1, keepdims=True), 1)
    ax.imshow(shown, cmap=CMAP, vmin=0)
    for i, j in np.ndindex(shown.shape):
        text = f"{shown[i, j]:.{RATE_DECIMALS}f}" if normalized else f"{shown[i, j]:,d}"
        # White text on dark cells keeps the annotation readable.
        dark = shown[i, j] > LIGHT_TEXT_FRACTION * shown.max()
        ax.text(j, i, text, ha="center", va="center", fontsize=CELL_FONT,
                color="white" if dark else "black")
    ax.set_xticks([0, 1], CLASS_LABELS, fontsize=FONT_TICK)
    ax.set_yticks([0, 1], CLASS_LABELS, fontsize=FONT_TICK, rotation=90, va="center")
    ax.set_xlabel("Predicted", fontsize=FONT_LABEL)
    ax.set_ylabel("Actual", fontsize=FONT_LABEL)
    ax.set_title(title, fontsize=FONT_ANNOT + 2)


def _grid(metrics: dict, fig_dir: Path, normalized: bool, stem: str) -> None:
    """Write one grid figure with a panel per model.

    Args:
        metrics: Output of ``evaluate_all``.
        fig_dir: Figure directory.
        normalized: Row-normalised rates if True, else counts.
        stem: Output stem.
    """
    fig, axes = make_grid(len(metrics))
    for ax, entry in zip(axes, metrics.values()):
        _draw(ax, _matrix(entry), entry["name"], normalized)
    kind = "row-normalised rates" if normalized else "counts"
    fig.suptitle(f"Confusion matrices on the test set ({kind})", fontsize=FONT_TITLE)
    common.save_figure(fig, fig_dir / stem)


def _single(key: str, entry: dict, fig_dir: Path) -> None:
    """Write the single-model figure with counts and rates side by side.

    Args:
        key: Model key.
        entry: One ``evaluate_all`` entry.
        fig_dir: Figure directory.
    """
    fig = Figure(figsize=(2 * SINGLE_SIZE, SINGLE_SIZE), layout="constrained")
    for i, (normalized, title) in enumerate(PANEL_TITLES.items()):
        _draw(fig.add_subplot(1, 2, i + 1), _matrix(entry), title, normalized)
    fig.suptitle(f"{entry['name']}: confusion matrix on the test set", fontsize=FONT_TITLE)
    common.save_figure(fig, fig_dir / f"confusion_{key}")


def plot_all(metrics: dict, fig_dir: Path) -> None:
    """Write both grids and one figure per model.

    Args:
        metrics: Output of ``evaluate_all``.
        fig_dir: Figure directory.
    """
    _grid(metrics, fig_dir, False, "confusion_grid_counts")
    _grid(metrics, fig_dir, True, "confusion_grid_normalized")
    for key, entry in metrics.items():
        _single(key, entry, fig_dir)
    log.info("wrote %d confusion figures to %s", len(metrics) + 2, fig_dir)
