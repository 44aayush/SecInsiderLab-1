"""Tests for script/export_model.py (synthetic data, no CSV)."""
from __future__ import annotations

import math

import numpy as np
import pytest
from sklearn.datasets import make_classification
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

import export_model as em
import kmodel
from common import KERNEL_FEATURES, LEAF_SHIFT, N_FEATURES

ONE = 1 << LEAF_SHIFT
N_ROWS = 2000


@pytest.fixture(name="data", scope="module")
def _data() -> tuple[np.ndarray, np.ndarray]:
    """Synthetic data in CIC units whose kernel-unit values are integers.

    Returns:
        (x, y) with x of shape (2000, 10) and balanced-ish labels.
    """
    x, y = make_classification(n_samples=N_ROWS, n_features=N_FEATURES, n_informative=6,
                               random_state=0)
    ints = np.round((x - x.min(axis=0)) * 20)
    # k/8 is exact in binary, so floor(x * 1000) has no rounding error and the model is exact.
    return ints / np.where(em.SCALES == 1, 1, 8), y.astype(np.int64)


@pytest.fixture(name="models", scope="module")
def _models(data: tuple[np.ndarray, np.ndarray]) -> tuple[DecisionTreeClassifier, XGBClassifier,
                                                           dict]:
    """Fit a DT and a 20-tree XGB and export them.

    Args:
        data: Synthetic (x, y).

    Returns:
        (dt, xgb, kernel model dict).
    """
    x, y = data
    dt = DecisionTreeClassifier(max_depth=6, random_state=42).fit(x, y)
    xgb = XGBClassifier(n_estimators=20, max_depth=4, learning_rate=0.1, tree_method="hist",
                        random_state=42).fit(x, y, verbose=False)
    model = em.build_kernel_model(em.export_dt(dt), em.export_xgb(xgb), {})
    kmodel.validate(model)
    return dt, xgb, model


def test_to_int_features_floor_and_scale() -> None:
    """Each column is multiplied by its scale and floored."""
    x = np.array([[3.9, 7.0, 1.0, 2.0, 1.2349, 2.0004, 0.5, 0.0, 9.9, 4.0]])
    out = em.to_int_features(x)
    assert out.dtype == np.int64
    assert out[0].tolist() == [3, 7, 1, 2, 1234, 2000, 500, 0, 9900, 4]


def test_threshold_conversion_le_vs_lt() -> None:
    """DT is x <= t, XGB is x < t."""
    assert em.dt_threshold(5.5, 1) == 5
    assert em.xgb_threshold(5.0, 1) == 4  # x = 5 goes right
    assert em.xgb_threshold(5.5, 1) == 5
    assert em.dt_threshold(0.0015, 1000) == 1
    assert em.xgb_threshold(0.0015, 1000) == 1


def test_export_dt_matches_sklearn(data: tuple, models: tuple) -> None:
    """The integer DT agrees with predict on every row."""
    x, _ = data
    dt, _, model = models
    verdicts, _ = em.kernel_predictions(model, em.to_int_features(x))
    assert (verdicts == dt.predict(x)).all()


def test_export_xgb_matches_margin(data: tuple, models: tuple) -> None:
    """The integer margin is within 1e-3 of the float margin and the verdicts are equal."""
    x, _ = data
    _, xgb, model = models
    _, margin = em.kernel_predictions(model, em.to_int_features(x))
    ref = xgb.predict(x, output_margin=True)
    assert np.abs(margin / ONE - ref).max() <= 1e-3
    assert ((margin > 0) == (ref > 0)).all()
    assert len(model["xgb_roots"]) == 20


def test_base_margin_parsing() -> None:
    """Bracketed and plain base scores parse the same."""
    assert em.parse_base_score("[5.6E-1]") == em.parse_base_score("0.56") == 0.56
    assert round(math.log(0.56 / 0.44) * ONE) == round(math.log(em.parse_base_score("[5.6E-1]") /
                                                                (1 - 0.56)) * ONE)


def test_sample_test_vectors_balanced(data: tuple, models: tuple) -> None:
    """n rows per class (capped by class size); stored values equal the kmodel evaluation."""
    x, y = data
    _, _, model = models
    x_int = em.to_int_features(x)
    out = em.sample_test_vectors(x_int, y, model, 50, 42)
    assert len(out["x"]) == 100
    for row, dt, margin in zip(out["x"], out["dt"], out["xgb_margin"]):
        assert dt == kmodel.dt_verdict(model, row)
        assert margin == kmodel.xgb_margin(model, row)
    capped = em.sample_test_vectors(x_int, y, model, N_ROWS, 42)
    assert len(capped["x"]) == N_ROWS


def test_parity_lists_mismatches(data: tuple, models: tuple) -> None:
    """A clean model has no mismatches; a flipped DT leaf shows up in the mismatch rows."""
    x, y = data
    dt, xgb, model = models
    clean = em.parity(dt, xgb, model, x, y)
    assert clean["dt_agreement"] == 1.0 and clean["mismatches"] == []
    flipped = {**model, "nodes": [[-1, 0, 0, 0, 1 - n[4]] if n[0] == -1 and i < dt.tree_.node_count
                                  else n for i, n in enumerate(model["nodes"])]}
    res = em.parity(dt, xgb, flipped, x, y)
    assert res["n_dt_mismatch"] == N_ROWS and {m["model"] for m in res["mismatches"]} == {"DT"}


def test_feature_count_matches_scales() -> None:
    """SCALES mirrors KERNEL_FEATURES."""
    assert len(em.SCALES) == len(KERNEL_FEATURES) == N_FEATURES
