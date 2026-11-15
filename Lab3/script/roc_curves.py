"""ROC curves on the test split (Task 3: "compare and draw ROC curves").

Writes the six ROC stems of CLAUDE.md 5.1: ``roc_test``, ``roc_test_zoom``,
``roc_test_logx``, ``roc_grid``, ``roc_test_ml`` and ``roc_test_dl``. ML models
use solid lines, DL models dashed ones; the AUC is shown with 4 decimals.
"""
from __future__ import annotations

import logging
import math
from pathlib import Path

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from sklearn.metrics import roc_auc_score, roc_curve

import common
from plot_utils import (FONT_TICK, FONT_TITLE, LEGEND_ANCHOR, LINE_WIDTH, fmt, line_style,
                        make_grid, model_color, style_axis)

log = logging.getLogger(__name__)

Curve = tuple[common.ModelResult, np.ndarray, np.ndarray, float]
SINGLE_W, SINGLE_H = 10.0, 6.0
ZOOM_FPR_MAX, ZOOM_TPR_MIN = 0.01, 0.99   # tight enough to separate RF, XGBoost and KNN
LOGX_FPR_MIN = 1e-5                # FPR 0 cannot be drawn on a log axis (CLAUDE.md 9)
AXIS_PAD = 0.01                    # keeps curves on the frame visible
ZOOM_TPR_MAX = 1.0005              # a little room above TPR = 1 in the zoomed view
LOGX_Y_MAX = 1.02                  # keeps y from dropping below 0 on the log-x figure
CHANCE_POINTS = 100                # samples of the chance curve on the log axis


def _curves(results: list[common.ModelResult], y_test: np.ndarray) -> list[Curve]:
    """Compute the ROC curve and AUC of every model once.

    Args:
        results: Model results in run order.
        y_test: True test labels (1 = DDoS).

    Returns:
        List of (result, fpr, tpr, auc).
    """
    out = []
    for res in results:
        fpr, tpr, _ = roc_curve(y_test, res.y_test_score)
        out.append((res, fpr, tpr, float(roc_auc_score(y_test, res.y_test_score))))
    return out


def densify_log(fpr: np.ndarray, tpr: np.ndarray, n_points: int = CHANCE_POINTS
                ) -> tuple[np.ndarray, np.ndarray]:
    """Add log-spaced points inside the ROC segments for a log x-axis.

    A segment that is straight in linear FPR bends on a log axis, so it must be sampled;
    the original points are all kept, so vertical jumps stay vertical.

    Args:
        fpr: ROC false positive rates (non-decreasing).
        tpr: ROC true positive rates.
        n_points: Number of log-spaced sample positions (1e-5 to 1).

    Returns:
        (fpr, tpr) with the extra points inserted in order.
    """
    grid = np.logspace(math.log10(LOGX_FPR_MIN), 0, n_points)
    # Segment i runs from point i-1 to i; side="right" skips the vertical points at grid.
    idx = np.searchsorted(fpr, grid, side="right")
    keep = (idx > 0) & (idx < len(fpr))  # grid points outside the curve need no sample
    grid, idx = grid[keep], idx[keep]
    x0, x1, y0, y1 = fpr[idx - 1], fpr[idx], tpr[idx - 1], tpr[idx]
    new_y = y0 + (y1 - y0) * (grid - x0) / (x1 - x0)  # linear in linear FPR space
    return np.insert(fpr, idx, grid), np.insert(tpr, idx, new_y)


def _chance(ax: Axes, log_x: bool, label: str | None) -> None:
    """Draw the chance diagonal (a curve on a log x-axis).

    Args:
        ax: Target axes.
        log_x: True when the x-axis is logarithmic.
        label: Legend label, or None to keep it out of the legend.
    """
    if log_x:
        # TPR = FPR is a straight line only on linear axes; sample it on the log grid.
        grid = np.logspace(math.log10(LOGX_FPR_MIN), 0, CHANCE_POINTS)
    else:
        grid = np.array([0.0, 1.0])
    ax.plot(grid, grid, color="grey", ls=":", label=label)


def _draw(ax: Axes, curves: list[Curve], legend: bool, kind: str = "full") -> None:
    """Draw the curves and the chance diagonal on one axes.

    Args:
        ax: Target axes.
        curves: Curves to draw.
        legend: Add a legend (outside the axes) with the AUC per model.
        kind: "full", "zoom" or "logx". Zoom marks curves without a point in the window and
            leaves the (out of view) chance line out of the legend; logx densifies the curves.
    """
    log_x, zoom = kind == "logx", kind == "zoom"
    for res, fpr, tpr, auc in curves:
        label = f"{res.name} (AUC = {fmt(auc)})"
        if zoom and not np.any((fpr <= ZOOM_FPR_MAX) & (tpr >= ZOOM_TPR_MIN)):
            label += " (outside view)"  # drawn nowhere in the window, keep the legend honest
        xs, ys = densify_log(fpr, tpr) if log_x else (fpr, tpr)
        # Straight segments between ROC points are the standard drawing (also for KNN).
        ax.plot(np.clip(xs, LOGX_FPR_MIN, None) if log_x else xs, ys,
                color=model_color(res.key), ls=line_style(res.family), lw=LINE_WIDTH,
                label=label)
    _chance(ax, log_x, None if zoom else "Chance")
    style_axis(ax, "", "False positive rate", "True positive rate")
    if legend:
        ax.legend(loc="upper left", bbox_to_anchor=LEGEND_ANCHOR, fontsize=FONT_TICK)


def _overlay(curves: list[Curve], fig_dir: Path, stem: str, title: str,
             kind: str = "full") -> None:
    """Write one overlay figure, skipping it when there is nothing to draw.

    Args:
        curves: Curves to draw.
        fig_dir: Figure directory.
        stem: Output stem.
        title: Figure title.
        kind: "full", "zoom" or "logx" axis ranges.
    """
    if not curves:
        log.info("no models for %s, skipping", stem)
        return
    fig = Figure(figsize=(SINGLE_W, SINGLE_H), layout="constrained")
    ax = fig.add_subplot(1, 1, 1)
    _draw(ax, curves, legend=True, kind=kind)
    if kind == "zoom":
        ax.set_xlim(0, ZOOM_FPR_MAX)
        ax.set_ylim(ZOOM_TPR_MIN, ZOOM_TPR_MAX)
    elif kind == "logx":
        ax.set_xscale("log")
        ax.set_xlim(LOGX_FPR_MIN, 1)
        ax.set_ylim(0, LOGX_Y_MAX)
    else:
        ax.set_xlim(-AXIS_PAD, 1)
        ax.set_ylim(0, 1 + AXIS_PAD)
    ax.set_title(title, fontsize=FONT_TITLE)
    common.save_figure(fig, fig_dir / stem)


def _grid(curves: list[Curve], fig_dir: Path) -> None:
    """Write one ROC panel per model with its AUC in the title.

    Args:
        curves: Curves of all models.
        fig_dir: Figure directory.
    """
    fig, axes = make_grid(len(curves))
    for ax, item in zip(axes, curves):
        _draw(ax, [item], legend=False)
        ax.set_title(f"{item[0].name} (AUC = {fmt(item[3])})", fontsize=FONT_TICK + 1)
    fig.suptitle("ROC curve per model (test set)", fontsize=FONT_TITLE)
    common.save_figure(fig, fig_dir / "roc_grid")


def plot_roc(results: list[common.ModelResult], y_test: np.ndarray, out_dir: Path) -> None:
    """Write the six ROC figures to ``out_dir/figures``.

    Args:
        results: Model results in run order.
        y_test: True test labels (1 = DDoS).
        out_dir: Output root.
    """
    fig_dir = out_dir / "figures"
    curves = _curves(results, y_test)
    _overlay(curves, fig_dir, "roc_test", "ROC curves on the test set")
    _overlay(curves, fig_dir, "roc_test_zoom", "ROC curves, zoomed on the top-left corner", "zoom")
    _overlay(curves, fig_dir, "roc_test_logx", "ROC curves, log-scale FPR", "logx")
    _grid(curves, fig_dir)
    for family in ("ML", "DL"):
        subset = [c for c in curves if c[0].family == family]
        _overlay(subset, fig_dir, f"roc_test_{family.lower()}", f"ROC curves, {family} models")
