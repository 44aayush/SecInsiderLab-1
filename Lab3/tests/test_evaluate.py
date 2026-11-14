"""Tests for evaluate.py: hand-checked metrics, the 0.5 tie-break and JSON output."""
from __future__ import annotations

import json

import numpy as np
import pytest

import common
import evaluate

# 10 samples: TP=3, FN=1, FP=2, TN=4
Y_TRUE = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
Y_SCORE = np.array([0.9, 0.8, 0.7, 0.2, 0.6, 0.55, 0.4, 0.3, 0.1, 0.0])


def test_hand_checked_metrics() -> None:
    """Metrics and confusion matrix match values computed by hand."""
    m = evaluate.compute_metrics(Y_TRUE, Y_SCORE)
    assert (m["tn"], m["fp"], m["fn"], m["tp"]) == (4, 2, 1, 3)
    assert m["accuracy"] == pytest.approx(0.7)
    assert m["precision"] == pytest.approx(0.6)
    assert m["recall"] == pytest.approx(0.75)
    assert m["f1"] == pytest.approx(2 * 0.6 * 0.75 / 1.35)
    # BENIGN F1 = 2*4/(2*4+2+1) = 8/11; macro = mean of both classes
    assert m["macro_f1"] == pytest.approx((m["f1"] + 8 / 11) / 2)
    assert m["roc_auc"] == pytest.approx(20 / 24)  # 20 of 24 pos/neg pairs ranked correctly


def test_score_of_exactly_half_is_benign() -> None:
    """A score of exactly 0.5 predicts BENIGN (same tie-break as sklearn predict)."""
    m = evaluate.compute_metrics(np.array([1, 0]), np.array([0.5, 0.5]))
    assert (m["tn"], m["fp"], m["fn"], m["tp"]) == (1, 0, 1, 0)


def test_zero_division_gives_zero() -> None:
    """With no positive predictions, precision is 0.0 instead of a warning or NaN."""
    m = evaluate.compute_metrics(np.array([1, 0, 1, 0]), np.array([0.1, 0.2, 0.3, 0.4]))
    assert m["precision"] == 0.0


def test_evaluate_all_schema_and_json(splits: common.DataSplits) -> None:
    """evaluate_all keeps run order, has the schema keys and is JSON-serialisable."""
    rng = np.random.default_rng(common.SEED)
    results = [
        common.ModelResult(key, key.upper(), "ML", rng.random(len(splits.y_val)),
                           rng.random(len(splits.y_test)), 1.5, 0.25)
        for key in ("rf", "gnb")
    ]
    out = evaluate.evaluate_all(results, splits)
    assert list(out) == ["rf", "gnb"]
    assert set(out["rf"]) == {"name", "family", "val", "test", "train_time_s", "predict_time_s"}
    assert set(out["rf"]["test"]) == {"accuracy", "precision", "recall", "f1", "macro_f1",
                                      "roc_auc", "tn", "fp", "fn", "tp"}
    json.dumps(out)
