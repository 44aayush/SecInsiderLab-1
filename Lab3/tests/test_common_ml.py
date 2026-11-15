"""Tests for common.py (logging, figure saving) and clf/ml_common.py (run_sklearn)."""
from __future__ import annotations

import logging
from pathlib import Path

from matplotlib.figure import Figure
from sklearn.naive_bayes import GaussianNB

import common
from clf.ml_common import run_sklearn


def test_setup_logging_is_idempotent(tmp_path: Path) -> None:
    """Calling it twice leaves exactly two handlers and writes run_windows.log."""
    common.setup_logging(tmp_path)
    common.setup_logging(tmp_path)
    assert len(logging.getLogger().handlers) == 2
    logging.getLogger("t").info("hello")
    assert "hello" in (tmp_path / "run_windows.log").read_text(encoding="utf-8")


def test_save_figure_writes_png_and_pdf(tmp_path: Path) -> None:
    """save_figure creates the parent directory and both files."""
    fig = Figure()
    fig.add_subplot().plot([0, 1], [0, 1])
    common.save_figure(fig, tmp_path / "sub" / "fig")
    assert (tmp_path / "sub" / "fig.png").stat().st_size > 0
    assert (tmp_path / "sub" / "fig.pdf").stat().st_size > 0


def test_run_sklearn_contract(splits: common.DataSplits) -> None:
    """run_sklearn returns family ML, in-range scores of the split sizes and positive times."""
    res = run_sklearn(GaussianNB(), "gnb", "Gaussian Naive Bayes", splits)
    assert (res.key, res.family, res.history) == ("gnb", "ML", None)
    assert res.y_val_score.shape == splits.y_val.shape
    assert res.y_test_score.shape == splits.y_test.shape
    assert ((res.y_test_score >= 0) & (res.y_test_score <= 1)).all()
    assert res.train_time_s > 0 and res.predict_time_s > 0
