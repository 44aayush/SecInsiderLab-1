"""Shared pytest fixtures for the Lab 3 unit tests.

``fixtures/sample_ddos.csv`` is a byte-for-byte copy of
``../Lab2/tests/fixtures/sample_ddos.csv`` (3,187 rows,
CRLF, 34 inf rows) with sha256
``e11e365a1de7456954074532a1bd9c6583d7046d666b7a4ae8c360fcdd01db3f``.
Unit tests never read the 77 MB CSV.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

import common
import evaluate

N_SAMPLES, N_FEATURES, N_VAL = 600, 10, 90


@pytest.fixture(name="fixture_csv")
def _fixture_csv() -> Path:
    """Return the path of the small sample CSV.

    Returns:
        Path of tests/fixtures/sample_ddos.csv.
    """
    return Path(__file__).resolve().parent / "fixtures" / "sample_ddos.csv"


@pytest.fixture(name="splits")
def _splits() -> common.DataSplits:
    """Build a synthetic 420/90/90 DataSplits (float32 features, int64 labels).

    Returns:
        DataSplits made with make_classification(random_state=42).
    """
    x, y = make_classification(n_samples=N_SAMPLES, n_features=N_FEATURES, n_informative=6,
                               random_state=common.SEED)
    x = x.astype("float32")
    y = y.astype("int64")
    x_train, x_rest, y_train, y_rest = train_test_split(
        x, y, test_size=2 * N_VAL, random_state=common.SEED, stratify=y)
    x_val, x_test, y_val, y_test = train_test_split(
        x_rest, y_rest, test_size=N_VAL, random_state=common.SEED, stratify=y_rest)
    names = [f"f{i}" for i in range(N_FEATURES)]
    return common.DataSplits(x_train, x_val, x_test, y_train, y_val, y_test, names)


def _fake_result(ident: tuple[str, str, str], ys: tuple, sigma: float) -> common.ModelResult:
    """Build a ModelResult with noisy scores around the true labels.

    Args:
        ident: (key, display name, family) with family "ML" or "DL".
        ys: (validation labels, test labels).
        sigma: Noise level; larger means a worse model.

    Returns:
        ModelResult with scores clipped to [0, 1]; DL results get a 4-epoch history.
    """
    rng = np.random.default_rng(common.SEED)

    def score(y):
        return np.clip(0.8 * y + 0.1 + rng.normal(0, sigma, len(y)), 0, 1)

    key, name, family = ident
    y_val, y_test = ys
    history = {"train_loss": [0.7, 0.5, 0.4, 0.35], "val_loss": [0.68, 0.5, 0.42, 0.45]} \
        if family == "DL" else None
    return common.ModelResult(key, name, family, score(y_val), score(y_test), 1.5, 0.2, history)


@pytest.fixture(name="fake_results")
def _fake_results(splits: common.DataSplits) -> list[common.ModelResult]:
    """Three fake results: two ML models and one DL model.

    Args:
        splits: Synthetic splits.

    Returns:
        List of gnb, rf (ML) and mlp (DL) results.
    """
    ys = (splits.y_val, splits.y_test)
    return [_fake_result(("gnb", "Gaussian Naive Bayes", "ML"), ys, 0.35),
            _fake_result(("rf", "Random Forest", "ML"), ys, 0.15),
            _fake_result(("mlp", "MLP", "DL"), ys, 0.25)]


@pytest.fixture(name="fake_metrics")
def _fake_metrics(fake_results: list[common.ModelResult], splits: common.DataSplits) -> dict:
    """Metrics of the fake results as produced by evaluate_all.

    Args:
        fake_results: Fake model results.
        splits: Synthetic splits.

    Returns:
        evaluate_all output.
    """
    return evaluate.evaluate_all(fake_results, splits)
