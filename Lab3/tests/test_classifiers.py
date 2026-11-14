"""Tests for the five Task 1 classifier modules on the synthetic DataSplits."""
from __future__ import annotations

from types import ModuleType

import numpy as np
import pytest

import common
from clf import gnb_clf, knn_clf, lr_clf, rf_clf, xgb_clf

MIN_ACCURACY = 0.8
DECISION_THRESHOLD = 0.5
EXPECTED = {
    "gnb": (gnb_clf, "Gaussian Naive Bayes"),
    "lr": (lr_clf, "Logistic Regression"),
    "knn": (knn_clf, "K-Nearest Neighbors"),
    "rf": (rf_clf, "Random Forest"),
    "xgb": (xgb_clf, "XGBoost"),
}
MODULES = [pytest.param(mod, key, name, id=key) for key, (mod, name) in EXPECTED.items()]


@pytest.mark.parametrize(("module", "key", "name"), MODULES)
def test_key_and_name_match_table(module: ModuleType, key: str, name: str) -> None:
    """KEY and NAME equal the CLAUDE.md 5 table."""
    assert module.KEY == key
    assert module.NAME == name


@pytest.mark.parametrize(("module", "key", "name"), MODULES)
def test_run_returns_valid_result(module: ModuleType, key: str, name: str,
                                  splits: common.DataSplits) -> None:
    """run gives an ML ModelResult with right-shaped scores in [0, 1] and positive times."""
    result = module.run(splits)
    assert (result.key, result.name, result.family) == (key, name, "ML")
    assert result.y_val_score.shape == splits.y_val.shape
    assert result.y_test_score.shape == splits.y_test.shape
    for scores in (result.y_val_score, result.y_test_score):
        assert scores.min() >= 0.0
        assert scores.max() <= 1.0
    assert result.train_time_s > 0
    assert result.predict_time_s > 0


@pytest.mark.parametrize(("module", "key", "name"), MODULES)
def test_test_accuracy_floor(module: ModuleType, key: str, name: str,
                             splits: common.DataSplits) -> None:
    """Every classifier reaches at least 0.8 test accuracy on the synthetic set."""
    assert key and name
    result = module.run(splits)
    accuracy = float(np.mean((result.y_test_score >= DECISION_THRESHOLD) == splits.y_test))
    assert accuracy >= MIN_ACCURACY


def test_xgb_prints_nothing(splits: common.DataSplits, capsys: pytest.CaptureFixture[str]) -> None:
    """verbose=False keeps XGBoost silent on stdout."""
    xgb_clf.run(splits)
    assert capsys.readouterr().out == ""
