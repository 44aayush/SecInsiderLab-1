"""Tests that every plot module writes its stems as png and pdf (Task 3)."""
from __future__ import annotations

from pathlib import Path

import common
import plots_confusion
import plots_metrics
import plots_training
import roc_curves

METRIC_STEMS = ["metrics_bar_grouped", "metrics_small_multiples", "metrics_heatmap",
                "metrics_radar", "metrics_dot", "errors_bar", "time_bar"]
CONFUSION_STEMS = ["confusion_grid_counts", "confusion_grid_normalized"]
TRAINING_STEMS = ["dl_history_overlay", "dl_history_grid"]
ROC_STEMS = ["roc_test", "roc_test_zoom", "roc_test_logx", "roc_grid", "roc_test_ml"]


def _assert_written(fig_dir: Path, stems: list[str]) -> None:
    """Check png and pdf exist for each stem.

    Args:
        fig_dir: Figure directory.
        stems: Expected stems.
    """
    for stem in stems:
        assert (fig_dir / f"{stem}.png").stat().st_size > 0, stem
        assert (fig_dir / f"{stem}.pdf").stat().st_size > 0, stem


def test_all_plots_three_models(fake_results, fake_metrics, splits, tmp_path: Path) -> None:
    """2 ML + 1 DL: every figure module writes all its stems."""
    fig_dir = tmp_path / "figures"
    plots_metrics.plot_all(fake_metrics, fig_dir)
    plots_confusion.plot_all(fake_metrics, fig_dir)
    plots_training.plot_all(fake_results, fig_dir)
    roc_curves.plot_roc(fake_results, splits.y_test, tmp_path)
    _assert_written(fig_dir, METRIC_STEMS + CONFUSION_STEMS + TRAINING_STEMS)
    _assert_written(fig_dir, ROC_STEMS + ["roc_test_dl"])
    _assert_written(fig_dir, [f"confusion_{k}" for k in fake_metrics])


def test_ml_only_skips_dl_figures(fake_results, fake_metrics, splits, tmp_path: Path) -> None:
    """Without DL models the DL figures are skipped without error."""
    ml_results = fake_results[:2]
    ml_metrics = {k: fake_metrics[k] for k in ("gnb", "rf")}
    fig_dir = tmp_path / "figures"
    plots_training.plot_all(ml_results, fig_dir)
    roc_curves.plot_roc(ml_results, splits.y_test, tmp_path)
    plots_metrics.plot_all(ml_metrics, fig_dir)
    assert not list(fig_dir.glob("dl_history*")) and not list(fig_dir.glob("roc_test_dl*"))
    _assert_written(fig_dir, ROC_STEMS + METRIC_STEMS)


def test_single_model_works(fake_results, fake_metrics, splits, tmp_path: Path) -> None:
    """Every plot function also works for a single model."""
    fig_dir = tmp_path / "figures"
    one = {"rf": fake_metrics["rf"]}
    plots_metrics.plot_all(one, fig_dir)
    plots_confusion.plot_all(one, fig_dir)
    roc_curves.plot_roc(fake_results[1:2], splits.y_test, tmp_path)
    _assert_written(fig_dir, METRIC_STEMS + CONFUSION_STEMS + ["confusion_rf", "roc_grid"])


def test_eight_models_grid_rows(fake_metrics, tmp_path: Path) -> None:
    """Eight models give a 4x2 confusion grid and all metric charts."""
    eight = {key: {**fake_metrics["rf"], "name": key} for key in common.MODEL_COLORS}
    for key, entry in eight.items():
        entry["family"] = "DL" if key in ("mlp", "lstm", "cnn") else "ML"
    fig_dir = tmp_path / "figures"
    plots_metrics.plot_all(eight, fig_dir)
    plots_confusion.plot_all(eight, fig_dir)
    _assert_written(fig_dir, METRIC_STEMS + CONFUSION_STEMS)
