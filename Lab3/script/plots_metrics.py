"""Metric comparison charts on the test split (Task 3, CLAUDE.md 5.1).

Seven charts: grouped bars, small multiples, heatmap, radar, dot plot, error
counts and run times. Scores are shown as 4-decimal values (user decision).
"""
from __future__ import annotations

import logging
import math
from pathlib import Path

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

import common
from plot_utils import (AXIS_TOP_PAD, BAR_LABEL_PAD, FONT_ANNOT, FONT_TICK, FONT_TITLE,
                        LEGEND_ANCHOR, LINE_WIDTH, SCORE_KEYS, SCORE_LABELS, SERIES_COLORS,
                        axis_floor, cap_score_ticks, fmt, line_style, model_color, style_axis)

log = logging.getLogger(__name__)

BAR_METRICS = ["accuracy", "precision", "recall", "f1"]
DOT_MARKERS = ["o", "s", "^", "D", "v", "P"]
SINGLE_W, SINGLE_H = 11.0, 6.0
XTICK_ROTATION = 30              # long model names would overlap when flat
MULTI_W, MULTI_H = 14.0, 9.0      # 2x2 small-multiples figure
LEGEND_BELOW = (0.5, -0.3)       # legend anchor under the axes, centred
DOT_SIZE = 70
RADAR_SIZE = 8.0
RADAR_TICKS = 4
RADAR_LABEL_ALPHA, RADAR_LABEL_Z = 0.85, 10   # white box opacity and draw order of radial labels
RADAR_TITLE_PAD = 24              # points between the polar rim and the title
RADAR_LABEL_PAD = 18             # points between the polar rim and the axis names
RADAR_LEGEND_ANCHOR = (0.5, -0.12)  # centred below the polar area, clear of every label
RADAR_LEGEND_COLS = 4
HEATMAP_CELL = 1.4                # inches per heatmap column
HEATMAP_ROW = 0.7                 # inches per heatmap row
BAR_TOTAL_WIDTH = 0.8
ANNOT_ROTATION = 90
LOG_LINTHRESH = 1                 # symlog is linear below 1 so a count of 0 can be drawn
HEATMAP_MARGIN = 2.0              # inches added around the heatmap for labels and colourbar
TIME_LOW, TIME_HIGH = 0.5, 8.0   # log axis: 0.5x min to 8x max (room for the value labels)
HEADROOM = 0.25                   # extra axis span reserved for bar annotations


def _test(metrics: dict, key: str) -> dict:
    """Return the test-split metrics of one model.

    Args:
        metrics: Output of ``evaluate_all``.
        key: Model key.

    Returns:
        The ``test`` dict.
    """
    return metrics[key]["test"]


def _all_scores(metrics: dict, names: list[str]) -> list[float]:
    """Collect the listed test scores of all models.

    Args:
        metrics: Output of ``evaluate_all``.
        names: Metric names.

    Returns:
        Flat list of values.
    """
    return [_test(metrics, k)[n] for k in metrics for n in names]


def _single_figure() -> tuple[Figure, Axes]:
    """Create a single-axes figure of the standard size.

    Returns:
        Figure and its axes.
    """
    fig = Figure(figsize=(SINGLE_W, SINGLE_H), layout="constrained")
    return fig, fig.add_subplot(1, 1, 1)


def plot_bar_grouped(metrics: dict, fig_dir: Path) -> None:
    """Grouped vertical bars: Accuracy, Precision, Recall and F1 per model.

    Args:
        metrics: Output of ``evaluate_all``.
        fig_dir: Figure directory.
    """
    fig, ax = _single_figure()
    keys = list(metrics)
    width = BAR_TOTAL_WIDTH / len(BAR_METRICS)
    floor = axis_floor(_all_scores(metrics, BAR_METRICS))
    for j, name in enumerate(BAR_METRICS):
        xs = np.arange(len(keys)) + (j - (len(BAR_METRICS) - 1) / 2) * width
        vals = [_test(metrics, k)[name] for k in keys]
        label = SCORE_LABELS[SCORE_KEYS.index(name)]
        bars = ax.bar(xs, vals, width, color=SERIES_COLORS[j], label=label)
        ax.bar_label(bars, labels=[fmt(v) for v in vals], rotation=ANNOT_ROTATION,
                     padding=BAR_LABEL_PAD, fontsize=FONT_ANNOT)
    ax.set_xticks(range(len(keys)), [metrics[k]["name"] for k in keys],
                   rotation=XTICK_ROTATION, ha="right")
    # Headroom above 1.0 holds the rotated value labels.
    ax.set_ylim(floor, 1.0 + HEADROOM * (1.0 - floor))
    ax.axhline(1.0, color="grey", lw=1, ls=":")  # reference line at perfect score
    cap_score_ticks(ax, "y")  # the headroom must not add a tick above 1.000
    style_axis(ax, "Test scores per model", "Model", "Score")
    ax.legend(loc="upper center", bbox_to_anchor=LEGEND_BELOW, ncols=len(BAR_METRICS),
              fontsize=FONT_TICK)
    common.save_figure(fig, fig_dir / "metrics_bar_grouped")


def plot_small_multiples(metrics: dict, fig_dir: Path) -> None:
    """2x2 grid of sorted horizontal bars, one panel per metric.

    Args:
        metrics: Output of ``evaluate_all``.
        fig_dir: Figure directory.
    """
    fig = Figure(figsize=(MULTI_W, MULTI_H), layout="constrained")
    for j, name in enumerate(BAR_METRICS):
        ax = fig.add_subplot(2, 2, j + 1)
        order = sorted(metrics, key=lambda k, n=name: _test(metrics, k)[n])
        vals = [_test(metrics, k)[name] for k in order]
        floor = axis_floor(vals)
        bars = ax.barh([metrics[k]["name"] for k in order], vals,
                       color=[model_color(k) for k in order])
        ax.bar_label(bars, labels=[fmt(v) for v in vals], padding=BAR_LABEL_PAD,
                     fontsize=FONT_ANNOT)
        ax.set_xlim(floor, 1.0 + HEADROOM * (1.0 - floor))
        style_axis(ax, SCORE_LABELS[SCORE_KEYS.index(name)], "Score")
        cap_score_ticks(ax, "x")  # headroom holds the value labels only
    common.save_figure(fig, fig_dir / "metrics_small_multiples")


def plot_heatmap(metrics: dict, fig_dir: Path) -> None:
    """Annotated heatmap: models x the six scores.

    Args:
        metrics: Output of ``evaluate_all``.
        fig_dir: Figure directory.
    """
    keys = list(metrics)
    data = np.array([[_test(metrics, k)[n] for n in SCORE_KEYS] for k in keys])
    fig = Figure(figsize=(HEATMAP_CELL * len(SCORE_KEYS) + HEATMAP_MARGIN,
                        HEATMAP_ROW * len(keys) + HEATMAP_MARGIN),
                 layout="constrained")
    ax = fig.add_subplot(1, 1, 1)
    vmin = axis_floor(data.ravel().tolist())
    image = ax.imshow(data, cmap="viridis", vmin=vmin, vmax=1.0, aspect="auto")
    mid = (vmin + 1.0) / 2
    for i, j in np.ndindex(data.shape):
        # Dark text on bright cells and white on dark ones keeps every cell legible.
        ax.text(j, i, fmt(data[i, j]), ha="center", va="center", fontsize=FONT_ANNOT,
                color="black" if data[i, j] > mid else "white")
    ax.set_xticks(range(len(SCORE_KEYS)), SCORE_LABELS)
    ax.set_yticks(range(len(keys)), [metrics[k]["name"] for k in keys])
    ax.tick_params(labelsize=FONT_TICK)
    ax.set_title("Test scores, models x metrics", fontsize=FONT_TITLE)
    fig.colorbar(image, ax=ax, label="Score")
    common.save_figure(fig, fig_dir / "metrics_heatmap")


def plot_radar(metrics: dict, fig_dir: Path) -> None:
    """Radar chart with one polygon per model and a zoomed radial axis.

    Args:
        metrics: Output of ``evaluate_all``.
        fig_dir: Figure directory.
    """
    fig = Figure(figsize=(RADAR_SIZE, RADAR_SIZE), layout="constrained")
    ax = fig.add_subplot(1, 1, 1, projection="polar")
    angles = np.linspace(0, 2 * math.pi, len(SCORE_KEYS), endpoint=False)
    closed = np.append(angles, angles[0])  # repeat the first angle to close the polygon
    floor = axis_floor(_all_scores(metrics, SCORE_KEYS))
    for key, info in metrics.items():
        vals = [_test(metrics, key)[n] for n in SCORE_KEYS]
        ax.plot(closed, vals + vals[:1], color=model_color(key), ls=line_style(info["family"]),
                lw=LINE_WIDTH, marker="o", label=info["name"])
    ax.set_ylim(floor, 1.0)
    ticks = np.linspace(floor, 1.0, RADAR_TICKS + 1)[1:]
    ax.set_yticks(ticks, [fmt(t) for t in ticks])
    ax.set_xticks(angles, SCORE_LABELS)
    # Radial labels sit between two spokes so they do not collide with the axis names.
    ax.set_rlabel_position(math.degrees(angles[1]) / 2)
    for label in ax.get_yticklabels():
        # A white box keeps the radial values readable where polygons cross them.
        label.set_bbox({"facecolor": "white", "edgecolor": "none",
                        "alpha": RADAR_LABEL_ALPHA})
        label.set_zorder(RADAR_LABEL_Z)
    ax.tick_params(labelsize=FONT_TICK)
    ax.tick_params(axis="x", pad=RADAR_LABEL_PAD)  # keeps "Accuracy" etc. off the rim
    ax.set_title("Model profiles (test, radial axis zoomed)", fontsize=FONT_TITLE,
                 pad=RADAR_TITLE_PAD)
    # Legend below the polar area (not beside it) so it cannot touch the axis names.
    ax.legend(loc="upper center", bbox_to_anchor=RADAR_LEGEND_ANCHOR, ncol=RADAR_LEGEND_COLS,
              fontsize=FONT_TICK)
    common.save_figure(fig, fig_dir / "metrics_radar")


def plot_dot(metrics: dict, fig_dir: Path) -> None:
    """Cleveland dot plot: one row per model, one marker per metric.

    Args:
        metrics: Output of ``evaluate_all``.
        fig_dir: Figure directory.
    """
    fig, ax = _single_figure()
    keys = sorted(metrics, key=lambda k: _test(metrics, k)["f1"])
    ys = np.arange(len(keys))
    for j, name in enumerate(SCORE_KEYS):
        ax.scatter([_test(metrics, k)[name] for k in keys], ys, marker=DOT_MARKERS[j],
                   color=SERIES_COLORS[j], s=DOT_SIZE, label=SCORE_LABELS[j], zorder=3,
                   clip_on=False)  # a marker at 1.0 must not be cut by the axis edge
    ax.set_yticks(ys, [metrics[k]["name"] for k in keys])
    floor = axis_floor(_all_scores(metrics, SCORE_KEYS))
    ax.set_xlim(floor, 1.0 + AXIS_TOP_PAD)
    cap_score_ticks(ax, "x")
    style_axis(ax, "Test scores per model (sorted by F1)", "Score")
    ax.legend(loc="upper left", bbox_to_anchor=LEGEND_ANCHOR, fontsize=FONT_TICK)
    common.save_figure(fig, fig_dir / "metrics_dot")


def plot_errors(metrics: dict, fig_dir: Path) -> None:
    """Grouped FP/FN bars on a log-like y-axis.

    Args:
        metrics: Output of ``evaluate_all``.
        fig_dir: Figure directory.
    """
    fig, ax = _single_figure()
    keys = list(metrics)
    width = BAR_TOTAL_WIDTH / 2
    for j, (name, label) in enumerate([("fp", "False positives"), ("fn", "False negatives")]):
        vals = [_test(metrics, k)[name] for k in keys]
        bars = ax.bar(np.arange(len(keys)) + (j - 0.5) * width, vals, width,
                      color=SERIES_COLORS[j], label=label)
        ax.bar_label(bars, labels=[str(v) for v in vals], padding=BAR_LABEL_PAD,
                     fontsize=FONT_ANNOT)
    # symlog is log above LINTHRESH but can still draw a bar of height 0.
    ax.set_yscale("symlog", linthresh=LOG_LINTHRESH)
    ax.set_ylim(bottom=0)
    ax.set_xticks(range(len(keys)), [metrics[k]["name"] for k in keys],
                   rotation=XTICK_ROTATION, ha="right")
    style_axis(ax, "Errors on the test set (log scale)", "Model", "Count")
    ax.margins(y=HEADROOM)
    ax.legend(fontsize=FONT_TICK, loc="upper center", bbox_to_anchor=LEGEND_BELOW, ncols=2)
    common.save_figure(fig, fig_dir / "errors_bar")


def plot_time(metrics: dict, fig_dir: Path) -> None:
    """Horizontal bars of train and predict time on a log x-axis.

    Args:
        metrics: Output of ``evaluate_all``.
        fig_dir: Figure directory.
    """
    fig, ax = _single_figure()
    keys = list(metrics)
    height = BAR_TOTAL_WIDTH / 2
    series = [("train_time_s", "Train time"), ("predict_time_s", "Predict time")]
    for j, (name, label) in enumerate(series):
        vals = [metrics[k][name] for k in keys]
        bars = ax.barh(np.arange(len(keys)) + (j - 0.5) * height, vals, height,
                       color=SERIES_COLORS[j], label=label)
        ax.bar_label(bars, labels=[f"{v:.3f} s" for v in vals], padding=BAR_LABEL_PAD,
                     fontsize=FONT_ANNOT)
    ax.set_xscale("log")
    positive = [metrics[k][n] for k in keys for n, _ in series if metrics[k][n] > 0]
    ax.set_xlim(TIME_LOW * min(positive), TIME_HIGH * max(positive))  # tight to the data
    ax.set_yticks(range(len(keys)), [metrics[k]["name"] for k in keys])
    style_axis(ax, "Cost per model (log scale)", "Seconds")
    # Legend beside the axes: below it, a gap opens up under the x-label.
    ax.legend(fontsize=FONT_TICK, loc="upper left", bbox_to_anchor=LEGEND_ANCHOR)
    common.save_figure(fig, fig_dir / "time_bar")


def plot_all(metrics: dict, fig_dir: Path) -> None:
    """Write all seven metric charts.

    Args:
        metrics: Output of ``evaluate_all``.
        fig_dir: Figure directory.
    """
    for func in (plot_bar_grouped, plot_small_multiples, plot_heatmap, plot_radar,
                 plot_dot, plot_errors, plot_time):
        func(metrics, fig_dir)
    log.info("wrote 7 metric charts to %s", fig_dir)
