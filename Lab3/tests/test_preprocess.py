"""Tests for preprocess.py: cleaning steps, labels, split, scaling and the summary schema."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import common
import preprocess

SUMMARY_KEYS = {
    "raw_shape", "raw_class_counts", "inf_counts", "nan_counts", "inf_nan_rows",
    "duplicate_rows", "constant_columns", "identical_columns", "clean_shape",
    "clean_class_counts", "split_sizes", "split_class_counts", "feature_names",
}
FRAC_TOLERANCE = 0.01


def _frame(**cols: list) -> pd.DataFrame:
    """Build a DataFrame from column lists (a Label column is expected among them).

    Args:
        **cols: Column name to values.

    Returns:
        The DataFrame.
    """
    return pd.DataFrame(cols)


def test_inf_and_nan_rows_dropped_and_counted_per_class() -> None:
    """+inf, -inf and NaN rows disappear and are counted by class."""
    df = _frame(a=[1.0, np.inf, -np.inf, np.nan, 5.0, 6.0], b=[1.0, 2.0, 3.0, 4.0, 5.0, 7.0],
                Label=["BENIGN", "BENIGN", "DDoS", "DDoS", "DDoS", "BENIGN"])
    out, summ = preprocess.clean(df)
    assert len(out) == 3
    assert summ["inf_nan_rows"] == {"n": 3, "by_class": {"BENIGN": 1, "DDoS": 2}}
    assert summ["inf_counts"] == {"a": 2}
    assert summ["nan_counts"] == {"a": 1}


def _dup_frame() -> pd.DataFrame:
    """Return a frame whose last two rows duplicate the first two.

    Returns:
        DataFrame with one BENIGN and one DDoS duplicate row.
    """
    return _frame(a=[1.0, 2.0, 3.0, 1.0, 2.0], b=[5.0, 6.0, 8.0, 5.0, 6.0],
                  Label=["BENIGN", "DDoS", "DDoS", "BENIGN", "DDoS"])


def test_duplicates_dropped() -> None:
    """Duplicate rows are dropped and counted per class."""
    out, summ = preprocess.clean(_dup_frame())
    assert len(out) == 3
    assert summ["duplicate_rows"] == {"n": 2, "by_class": {"BENIGN": 1, "DDoS": 1}}


def test_duplicates_kept_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """With DROP_DUPLICATES False every row stays and the count is 0."""
    monkeypatch.setattr(common, "DROP_DUPLICATES", False)
    out, summ = preprocess.clean(_dup_frame())
    assert len(out) == 5
    assert summ["duplicate_rows"]["n"] == 0


def test_constant_columns_dropped() -> None:
    """A column with one distinct value is removed and listed."""
    df = _frame(a=[1.0, 2.0, 3.0], const=[7.0, 7.0, 7.0], Label=["BENIGN", "DDoS", "DDoS"])
    out, summ = preprocess.clean(df)
    assert summ["constant_columns"] == ["const"]
    assert list(out.columns) == ["a", "Label"]


def test_identical_columns_tolerance_and_first_kept() -> None:
    """Exact and 1e-9 copies are dropped, a 1e-3 difference is kept, first occurrence wins."""
    base = np.array([1.0, 5.0, 2.0, 9.0])
    df = _frame(a=base, exact=base.copy(), near=base + 1e-9, far=base + 1e-3,
                Label=["BENIGN", "DDoS", "BENIGN", "DDoS"])
    out, summ = preprocess.clean(df)
    assert summ["identical_columns"] == {"exact": "a", "near": "a"}
    assert list(out.columns) == ["a", "far", "Label"]


def test_clean_shape_excludes_label() -> None:
    """clean_shape counts rows and feature columns only."""
    df = _frame(a=[1.0, 2.0, 3.0], b=[4.0, 1.0, 0.0], Label=["BENIGN", "DDoS", "DDoS"])
    _, summ = preprocess.clean(df)
    assert summ["clean_shape"] == [3, 2]
    assert summ["clean_class_counts"] == {"BENIGN": 1, "DDoS": 2}


def test_unknown_label_raises() -> None:
    """Any label other than BENIGN/DDoS is rejected."""
    with pytest.raises(ValueError):
        preprocess.encode_labels(pd.Series(["BENIGN", "PortScan"]))


def test_encode_labels_values() -> None:
    """BENIGN is 0, DDoS is 1, dtype int64."""
    y = preprocess.encode_labels(pd.Series(["BENIGN", "DDoS"]))
    assert y.tolist() == [0, 1] and y.dtype == np.int64


@pytest.fixture(name="labels")
def _labels() -> np.ndarray:
    """Return 1,000 labels with a 60 % positive rate.

    Returns:
        int64 array.
    """
    return np.array([1] * 600 + [0] * 400, dtype=np.int64)


def test_split_sizes_stratified_and_disjoint(labels: np.ndarray) -> None:
    """Sizes are 70/15/15 (+-1 row), class ratios match within 1 pp, indices are disjoint."""
    train, val, test = preprocess.split_data(labels)
    for idx, frac in ((train, 0.70), (val, 0.15), (test, 0.15)):
        assert abs(len(idx) - frac * len(labels)) <= 1
        assert abs(labels[idx].mean() - labels.mean()) < FRAC_TOLERANCE
    assert not set(train) & set(val) and not set(train) & set(test) and not set(val) & set(test)
    assert len(set(train) | set(val) | set(test)) == len(labels)


def test_scaler_fitted_on_train_only() -> None:
    """Train means are ~0 while val/test means are not forced to 0."""
    rng = np.random.default_rng(common.SEED)
    y = rng.integers(0, 2, 400)
    feats = pd.DataFrame({"a": rng.normal(size=400), "b": rng.normal(size=400)})
    indices = (np.arange(0, 200), np.arange(200, 300), np.arange(300, 400))
    feats.iloc[200:, :] += 3.0  # shift held-out rows so a train-fitted scaler leaves them off-zero
    splits = preprocess.scale_splits(feats, y, indices)
    assert np.allclose(splits.x_train.mean(axis=0), 0.0, atol=1e-5)
    assert abs(splits.x_val.mean()) > 1.0 and abs(splits.x_test.mean()) > 1.0
    assert splits.x_train.dtype == np.float32 and splits.y_train.dtype == np.int64


def test_preprocess_fixture_csv(fixture_csv: Path) -> None:
    """End to end on the sample CSV: finite float32 arrays, binary labels, exact summary keys."""
    splits, summ = preprocess.preprocess(fixture_csv)
    for x in (splits.x_train, splits.x_val, splits.x_test):
        assert x.dtype == np.float32 and np.isfinite(x).all()
    for y in (splits.y_train, splits.y_val, splits.y_test):
        assert set(np.unique(y)) <= {0, 1}
    assert set(summ) == SUMMARY_KEYS
    assert summ["clean_shape"][1] == len(summ["feature_names"]) == splits.x_train.shape[1]
    assert sum(summ["split_sizes"].values()) == summ["clean_shape"][0]
    json.dumps(summ)
