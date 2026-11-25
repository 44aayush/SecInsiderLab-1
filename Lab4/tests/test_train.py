"""Tests for script/train.py."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from sklearn.datasets import make_classification

import common
import kmodel
import preprocess as pp
import train

Y_TRUE = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
Y_SCORE = np.array([0.9, 0.8, 0.7, 0.2, 0.6, 0.55, 0.4, 0.3, 0.1, 0.0])
FILES = ("preprocess_summary.json", "depth_selection.json", "metrics.json", "comparison_test.csv",
         "comparison_test.md", "comparison_val.csv", "comparison_val.md", "feature_importance.md",
         "parity.json", "parity_mismatches.csv")


@pytest.fixture(name="small_splits")
def _small_splits() -> pp.KernelSplits:
    """Synthetic kernel splits.

    Returns:
        KernelSplits with 500 train rows.
    """
    x, y = make_classification(n_samples=700, n_features=common.N_FEATURES, random_state=0)
    return pp.KernelSplits(x[:500], x[500:600], x[600:], y[:500], y[500:600], y[600:],
                           [n for n, _ in common.KERNEL_FEATURES])


def test_compute_metrics_hand_checked() -> None:
    """Hand-checked 10-sample case; a score of exactly 0.5 is BENIGN."""
    m = train.compute_metrics(Y_TRUE, Y_SCORE)
    assert (m["tn"], m["fp"], m["fn"], m["tp"]) == (4, 2, 1, 3)
    assert m["accuracy"] == pytest.approx(0.7)
    assert m["precision"] == pytest.approx(0.6)
    assert m["recall"] == pytest.approx(0.75)
    assert m["f1"] == pytest.approx(2 * 0.6 * 0.75 / 1.35)
    assert m["macro_f1"] == pytest.approx((m["f1"] + 8 / 11) / 2)
    assert m["roc_auc"] == pytest.approx(20 / 24)
    half = train.compute_metrics(np.array([1, 0]), np.array([0.5, 0.5]))
    assert (half["tn"], half["fp"], half["fn"], half["tp"]) == (1, 0, 1, 0)


def test_select_depth() -> None:
    """Smallest depth within the tolerance of the best; ties go to the smallest."""
    tol = common.DEPTH_F1_TOL
    assert train.select_depth({4: .9990, 5: .9994, 6: .9995}, tol) == 4
    assert train.select_depth({4: .9900, 5: .9994, 6: .9995}, tol) == 5
    assert train.select_depth({6: .9, 4: .9, 5: .9}, tol) == 4


def test_fit_xgb_exactly_20_trees(small_splits: pp.KernelSplits) -> None:
    """No early stopping: exactly 20 rounds."""
    model = train.fit_xgb(small_splits, 4)
    assert model.get_booster().num_boosted_rounds() == common.XGB_TREES
    assert not hasattr(model, "best_iteration")


def test_fit_dt_respects_depth(small_splits: pp.KernelSplits) -> None:
    """The tree is never deeper than max_depth."""
    assert train.fit_dt(small_splits, 3).get_depth() <= 3


def test_main_smoke(fixture_csv: Path, tmp_path: Path) -> None:
    """The pipeline runs on the fixture and writes every output."""
    models = tmp_path / "models"
    assert train.main(["--csv", str(fixture_csv), "--out", str(tmp_path),
                       "--models-dir", str(models)]) == 0
    for name in FILES:
        assert (tmp_path / "metrics" / name).is_file(), name
    kmodel.load(models / "kernel_model.json")
    vectors = json.loads((models / "test_vectors.json").read_text(encoding="utf-8"))
    assert set(vectors) == {"x", "dt", "xgb_margin"}
