"""Training-history figures of the DL models (Task 3 support, CLAUDE.md 5.1).

``dl_history_overlay`` compares the validation loss of all DL models;
``dl_history_grid`` shows train and val loss per model with the best epoch
(argmin of the val loss, the epoch ``EarlyStopper`` restores) marked.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

import common
from plot_utils import (FONT_TICK, FONT_TITLE, LEGEND_ANCHOR, LINE_WIDTH, SERIES_COLORS,
                        line_style, make_grid, model_color, style_axis)

log = logging.getLogger(__name__)

SINGLE_W, SINGLE_H = 9.0, 5.5
BEST_MARKER_SIZE = 14
# Not model colours (common.MODEL_COLORS): these lines stand for train/val, not for a model.
TRAIN_COLOR, VAL_COLOR = SERIES_COLORS[0], SERIES_COLORS[1]
BEST_Z = 5                         # best-epoch star is drawn above every line


def _epochs(values: list[float]) -> np.ndarray:
    """Return 1-based epoch numbers for a loss list.

    Args:
        values: Loss per epoch.

    Returns:
        Array 1..len(values).
    """
    return np.arange(1, len(values) + 1)


def _best_epoch(val_loss: list[float]) -> int:
    """Return the 1-based epoch with the lowest validation loss.

    Args:
        val_loss: Validation loss per epoch.

    Returns:
        Best epoch number.
    """
    return int(np.argmin(val_loss)) + 1


def _overlay(dl_results: list[common.ModelResult], fig_dir: Path) -> None:
    """Write the validation-loss overlay of all DL models.

    Args:
        dl_results: Results that carry a history.
        fig_dir: Figure directory.
    """
    fig = Figure(figsize=(SINGLE_W, SINGLE_H), layout="constrained")
    ax = fig.add_subplot(1, 1, 1)
    for res in dl_results:
        val = res.history["val_loss"]
        color = model_color(res.key)
        ax.plot(_epochs(val), val, color=color, ls=line_style(res.family), lw=LINE_WIDTH,
                marker="o", label=res.name)
        best = _best_epoch(val)
        ax.plot(best, val[best - 1], marker="*", color=color, ms=BEST_MARKER_SIZE, zorder=BEST_Z,
                markeredgecolor="white")  # white rim keeps the star visible on its own line
    style_axis(ax, "Validation loss of the DL models (star = best epoch)", "Epoch",
               "Validation loss")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))  # epochs are whole numbers
    ax.set_yscale("log")  # later epochs differ by small amounts; log shows them
    ax.legend(loc="upper left", bbox_to_anchor=LEGEND_ANCHOR, fontsize=FONT_TICK)
    common.save_figure(fig, fig_dir / "dl_history_overlay")


def _grid(dl_results: list[common.ModelResult], fig_dir: Path) -> None:
    """Write one panel per DL model with train and val loss.

    Args:
        dl_results: Results that carry a history.
        fig_dir: Figure directory.
    """
    fig, axes = make_grid(len(dl_results))
    for ax, res in zip(axes, dl_results):
        train, val = res.history["train_loss"], res.history["val_loss"]
        ax.plot(_epochs(train), train, color=TRAIN_COLOR, marker="o", lw=LINE_WIDTH,
                label="Train loss")
        ax.plot(_epochs(val), val, color=VAL_COLOR, marker="s", lw=LINE_WIDTH, label="Val loss")
        best = _best_epoch(val)
        ax.axvline(best, color="grey", ls=":", label=f"Best epoch ({best})")
        style_axis(ax, res.name, "Epoch", "Loss (log scale)")
        ax.set_yscale("log")  # later epochs differ by small amounts; log shows them
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend(fontsize=FONT_TICK)
    fig.suptitle("Training history per DL model", fontsize=FONT_TITLE)
    common.save_figure(fig, fig_dir / "dl_history_grid")


def plot_all(results: list[common.ModelResult], fig_dir: Path) -> None:
    """Write both history figures, or skip when no model has a history.

    Args:
        results: All model results in run order.
        fig_dir: Figure directory.
    """
    dl_results = [r for r in results if r.history]
    if not dl_results:
        log.info("no DL history available, skipping dl_history_* figures")
        return
    _overlay(dl_results, fig_dir)
    _grid(dl_results, fig_dir)
